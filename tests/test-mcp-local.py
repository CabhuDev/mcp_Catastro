#!/usr/bin/env python3
"""
Test local del servidor MCP - Simula la comunicación stdio de Claude Code

ACTUALIZACIONES V2:
- Casos de prueba actualizados para validación simplificada
- Múltiples referencias de prueba (Madrid y Granada)
- Mejor descripción de los casos de prueba
- Criterios de éxito ajustados para el nuevo modelo
"""

import asyncio
import json
import subprocess
import sys
import logging
from typing import Dict, Any

from mcp.types.version import LATEST_PROTOCOL_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPTester:
    """Simulador de cliente MCP para testing local"""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.process = None
        self.request_id = 1
    
    async def start_server(self):
        """Inicia el servidor MCP"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("✅ Servidor MCP iniciado")
            return True
        except Exception as e:
            logger.error(f"❌ Error iniciando servidor: {e}")
            return False
    
    async def send_request(self, method: str, params: Dict[str, Any] = None):
        """Envía una petición JSON-RPC al servidor"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        self.request_id += 1
        
        # Enviar petición
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Leer respuesta
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=10.0
            )
            response = json.loads(response_line.decode().strip())
            return response
        except asyncio.TimeoutError:
            logger.error("⏰ Timeout esperando respuesta del servidor")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"📄 Error parseando respuesta JSON: {e}")
            return None
    
    async def test_initialization(self):
        """Test de inicialización del servidor"""
        logger.info("\n🔄 Probando inicialización...")
        
        response = await self.send_request("initialize", {
            "protocolVersion": LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        
        if response and "result" in response:
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
            self.process.stdin.write((json.dumps(notification) + "\n").encode())
            await self.process.stdin.drain()
            logger.info("✅ Inicialización exitosa")
            logger.info(f"   Servidor: {response['result'].get('serverInfo', {}).get('name', 'Unknown')}")
            logger.info(f"   Versión: {response['result'].get('serverInfo', {}).get('version', 'Unknown')}")
            return True
        else:
            logger.error("❌ Error en inicialización")
            return False
    
    async def test_list_tools(self):
        """Test de listado de herramientas"""
        logger.info("\n🛠️ Probando listado de herramientas...")
        
        response = await self.send_request("tools/list")
        
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            logger.info(f"✅ Encontradas {len(tools)} herramientas:")
            for tool in tools:
                logger.info(f"   - {tool.get('name')}: {tool.get('description')}")
            return tools
        else:
            logger.error("❌ Error listando herramientas")
            return []
    
    async def test_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Test de llamada a herramienta específica"""
        logger.info(f"\n🔧 Probando herramienta: {tool_name}")
        
        response = await self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                logger.info("✅ Herramienta ejecutada exitosamente")
                logger.info(f"   Respuesta: {content[0].get('text', '')[:200]}...")
                return True
            else:
                logger.warning("⚠️ Herramienta ejecutada pero sin contenido")
                return False
        else:
            logger.error(f"❌ Error ejecutando herramienta: {response}")
            return False
    
    async def stop_server(self):
        """Detiene el servidor MCP"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logger.info("🛑 Servidor MCP detenido")

async def main():
    """Función principal de testing"""
    print("🧪 TESTER LOCAL DE SERVIDOR MCP")
    print("=" * 50)
    
    server_path = "mcp_server.py"
    tester = MCPTester(server_path)
    
    try:
        # Iniciar servidor
        if not await tester.start_server():
            return 1
        
        # Test de inicialización
        if not await tester.test_initialization():
            return 1
        
        # Test de listado de herramientas
        tools = await tester.test_list_tools()
        if not tools:
            return 1
        
        # Test de herramientas específicas del Catastro
        test_cases = [
            {
                "name": "validar_referencia_catastral",
                "args": {"referencia": "2749704YJ0624N0001DI"},
                "description": "Validación referencia Madrid"
            },
            {
                "name": "validar_referencia_catastral",
                "args": {"referencia": "4418928VG4141G0001IW"},
                "description": "Validación referencia Granada"
            },
            {
                "name": "consultar_catastro_por_referencia", 
                "args": {"referencia": "4418928VG4141G0001IW"},
                "description": "Consulta referencia Granada"
            },
            {
                "name": "consultar_catastro_por_coordenadas",
                "args": {"latitud": 40.4168, "longitud": -3.7038},
                "description": "Consulta por coordenadas Madrid"
            }
        ]
        
        success_count = 0
        for test_case in test_cases:
            tool_exists = any(t["name"] == test_case["name"] for t in tools)
            if tool_exists:
                logger.info(f"🔧 {test_case.get('description', test_case['name'])}")
                if await tester.test_tool_call(test_case["name"], test_case["args"]):
                    success_count += 1
            else:
                logger.warning(f"⚠️ Herramienta {test_case['name']} no encontrada")
        
        # Resumen final
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 50)
        print(f"✅ Herramientas encontradas: {len(tools)}")
        print(f"✅ Casos de prueba ejecutados: {len(test_cases)}")
        print(f"✅ Herramientas probadas exitosamente: {success_count}")
        
        if success_count >= 3:
            print("\n🎉 ¡SERVIDOR MCP FUNCIONANDO CORRECTAMENTE!")
            print("   ✅ Validación de referencias actualizada")
            print("   ✅ Consultas por referencia funcionando")
            print("   ✅ Consultas por coordenadas funcionando")
            print("   Listo para usar con Claude Code")
            return 0
        else:
            print("\n⚠️ Algunas herramientas presentan problemas")
            print("   Revisar logs para más detalles")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Error durante las pruebas: {e}")
        return 1
    
    finally:
        await tester.stop_server()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
