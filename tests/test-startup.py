#!/usr/bin/env python3
"""
Test básico de inicio - Verifica que el servidor MCP puede iniciarse
"""

import subprocess
import sys
import time
import os

def test_mcp_startup():
    """Prueba que el servidor MCP puede iniciarse correctamente"""
    
    print("🚀 VERIFICACIÓN DE INICIO DEL SERVIDOR MCP")
    print("=" * 50)
    
    # Verificar que el archivo existe
    server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_server.py")
    if not os.path.exists(server_path):
        print(f"❌ No se encuentra mcp_server.py en {server_path}")
        return False
    
    print(f"📄 Archivo servidor: {server_path}")
    
    # Verificar dependencias
    print("\n📦 Verificando dependencias...")
    try:
        import mcp
        print("   ✅ mcp: Instalado")
    except ImportError:
        print("   ❌ mcp: NO instalado (pip install mcp)")
        return False
    
    try:
        import httpx
        print("   ✅ httpx: Instalado")
    except ImportError:
        print("   ❌ httpx: NO instalado")
        return False
    
    try:
        import pydantic
        print("   ✅ pydantic: Instalado")
    except ImportError:
        print("   ❌ pydantic: NO instalado")
        return False
    
    # Intentar iniciar el servidor
    print("\n🔄 Intentando iniciar servidor MCP...")
    try:
        process = subprocess.Popen(
            [sys.executable, server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True
        )
        
        # Esperar un poco
        time.sleep(3)
        
        # Verificar si sigue corriendo
        if process.poll() is None:
            print("   ✅ Servidor iniciado correctamente")
            
            # Enviar señal de terminación suave
            try:
                process.terminate()
                process.wait(timeout=5)
                print("   ✅ Servidor detenido correctamente")
                return True
            except subprocess.TimeoutExpired:
                process.kill()
                print("   ⚠️ Servidor forzado a detenerse")
                return True
        else:
            # El proceso terminó, obtener error
            stdout, stderr = process.communicate()
            print("   ❌ Servidor falló al iniciar")
            if stderr:
                print(f"   Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error iniciando servidor: {e}")
        return False

def test_configuration():
    """Verifica la configuración básica"""
    print("\n⚙️ Verificando configuración...")
    
    try:
        # Cambiar al directorio del proyecto
        project_dir = os.path.dirname(os.path.dirname(__file__))
        os.chdir(project_dir)
        
        # Importar configuración
        sys.path.insert(0, project_dir)
        from config.settings import get_settings
        
        settings = get_settings()
        print(f"   ✅ URL base Catastro: {settings.catastro_base_url}")
        print(f"   ✅ Timeout: {settings.catastro_timeout}s")
        print(f"   ✅ Debug: {settings.debug}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error en configuración: {e}")
        return False

def main():
    """Función principal"""
    
    # Test 1: Configuración
    config_ok = test_configuration()
    
    # Test 2: Inicio del servidor
    startup_ok = test_mcp_startup()
    
    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 50)
    
    if config_ok and startup_ok:
        print("🎉 ¡TODO FUNCIONA CORRECTAMENTE!")
        print("   Tu servidor MCP está listo para Claude Code")
        print("\n🔥 Siguientes pasos:")
        print("   1. uv sync --locked")
        print("   2. uv run --locked python mcp_server.py")
        print("   3. claude --mcp-config claude-config.json")
        return 0
    else:
        print("⚠️ Hay problemas que corregir:")
        if not config_ok:
            print("   - Revisar configuración")
        if not startup_ok:
            print("   - Revisar dependencias y código")
        return 1

if __name__ == "__main__":
    sys.exit(main())
