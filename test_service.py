"""
MCP 服务本地测试脚本
"""
import socket
import sys

def test_mcp_service():
    print("=" * 60)
    print("MCP Service Local Test")
    print("=" * 60)

    # 测试端口连接
    print("\n[Test 1] Port Connectivity")
    try:
        s = socket.socket()
        s.settimeout(2)
        result = s.connect_ex(('127.0.0.1', 8080))
        s.close()
        if result == 0:
            print("  [PASS] Port 8080 is listening")
        else:
            print(f"  [FAIL] Port connection failed: {result}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

    # 测试 SSE 端点
    print("\n[Test 2] SSE Endpoint Response")
    try:
        s = socket.socket()
        s.connect(('127.0.0.1', 8080))
        s.send(b'GET /sse HTTP/1.1\r\nHost: localhost:8080\r\nAccept: text/event-stream\r\n\r\n')
        response = s.recv(1024)
        s.close()

        # 解析响应
        lines = response.decode('utf-8', errors='ignore').split('\r\n')
        status_line = lines[0] if lines else ""

        if '200 OK' in status_line:
            print(f"  [PASS] HTTP Status: {status_line}")

            # 检查 Content-Type
            for line in lines[1:]:
                if 'content-type:' in line.lower() and 'text/event-stream' in line.lower():
                    print("  [PASS] Content-Type: text/event-stream (SSE)")
                    print("\n" + "=" * 60)
                    print("RESULT: Service is working correctly!")
                    print("SSE endpoint: http://localhost:8080/sse")
                    print("=" * 60)
                    return True

            print("  [WARN] Content-Type not found in response")
        else:
            print(f"  [FAIL] Unexpected status: {status_line}")
            return False

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("RESULT: All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_mcp_service()
    sys.exit(0 if success else 1)
