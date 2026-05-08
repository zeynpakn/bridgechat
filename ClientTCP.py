import socket
import threading


# ───────────────── SABITLER VE GLOBAL DEGISKENLER ────────────────
 
HOST        = "127.0.0.1"       # client'in baglanacagi IP adresi
TCP_PORT    = 12345             # sunucunun TCP portu
BUFFER_SIZE = 1024


# ──────────────────────── MESAJ DINLEYICI ────────────────────────

def receive_messages(sock: socket.socket):
    """
    sunucudan gelen mesajlari arka planda dinler,
    ana thread'in mesaj gonderimini bloke etmez.
    \r ve flush=True ile terminaldeki input() bloklamasini asar.
    """
    while True:
        try:
            data = sock.recv(BUFFER_SIZE)       # sunucudan veri bekle
            if not data:
                print("\n\r[bilgi] sunucu baglantisi kapandi.")
                break
            # \r imleci satirin basina alir, flush ise aninda ekrana basar
            print(f"\r{data.decode()}\n> ", end="", flush=True)
        except Exception:
            print("\n\r[bilgi] sunucu ile baglanti kesildi.")
            break


# ──────────────────────────── MAIN ───────────────────────────────

if __name__ == "__main__":

    # ── sunucuya baglan ──
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, TCP_PORT))          # sunucu calismiyor ise hata verir
    except ConnectionRefusedError:
        print("[hata] sunucuya baglanilamadı, once sunucuyu baslatın.")
        exit(1)

    # ── kullanici adi dogrulama ──
    # Sunucudan gelen "Kullanici adinizi giriniz" talebini karsila
    try:
        initial_prompt = sock.recv(BUFFER_SIZE).decode()
        print(initial_prompt, end="", flush=True)
        
        while True:
            username = input().strip()
            if not username:
                continue
            
            sock.sendall(username.encode())
            
            # Sunucudan onay (Hosgeldiniz) veya hata mesaji bekle
            response = sock.recv(BUFFER_SIZE).decode()
            print(response, end="", flush=True)
            
            if "Hosgeldiniz" in response:
                break
            # Isim alinmissa sunucu tekrar soracaktir, dongu devam eder
    except Exception as e:
        print(f"\n[hata] Kayit sirasinda sorun olustu: {e}")
        sock.close()
        exit(1)

    # ── arka planda dinleyici thread baslat ──
    t = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    t.start()                                   # kullanici yazarken sunucudan gelen mesajlar ekrana duser

    # ── mesaj gonderme dongusu ──
    try:
        while True:
            message = input("> ")               # kullanicidan girdi al (imlec belirteci eklendi)
            if not message.strip():
                continue                        # bos mesaj gonderilmez
            sock.sendall(message.encode())
    except (KeyboardInterrupt, EOFError):
        print("\n[bilgi] cikiliyor...")
    finally:
        sock.close()                            # baglanti kapatilir, sunucudan ayril