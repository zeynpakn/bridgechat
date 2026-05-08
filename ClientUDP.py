import socket
import threading

# ───────────────── SABITLER VE GLOBAL DEGISKENLER ────────────────

HOST = "127.0.0.1"          # client'in baglanacagi IP adresi
UDP_PORT = 12346            # sunucunun UDP portu
BUFFER_SIZE = 1024
lock = threading.Lock()     # soketlere erisimi senkronize etmek icin


# ──────────────────────── MESAJ DINLEYICI ────────────────────────

def receive_messages(sock: socket.socket):
    """
    sunucudan gelen datagramlari arka planda dinler.
    \r ve flush=True kullanarak gelen mesajin ekrana aninda dusmesini saglar.
    """
    while True:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)    # sunucudan datagram bekle
            if not data:
                break
            with lock:                              # lock kullanarak veri alirken senkronize ol
                # \r satiri temizler, flush ise tamponu zorla ekrana yazar
                print(f"\r{data.decode()}\n> ", end="", flush=True)
        except Exception:
            print("\n\r[bilgi] sunucu ile baglanti kesildi.")
            break

# ──────────────────────────── MAIN ───────────────────────────────

if __name__ == "__main__":

    # ── soket olustur ──
    # isletim sistemi otomatik port atar, bind() gerekmez
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # ── kullanici adi gonder ──
    # UDP'de baglanti kavrami olmadigi icin ilk datagram kullanici adi olarak islenir
    while True:
        username = input("Kullanici adinizi giriniz: ").strip()
        if not username:
            continue                                 # bos giris kabul edilmez

        try:
            sock.sendto(username.encode(), (HOST, UDP_PORT))    # ilk datagram = kullanici adi

            # sunucunun cevabini bekle
            sock.settimeout(5)                       # sunucu cevap vermezse 5 saniye sonra hata ver
            response, _ = sock.recvfrom(BUFFER_SIZE)
            sock.settimeout(None)                    # normal bloklamaya geri don

            msg = response.decode()
            print(msg, end="", flush=True)

            if "Hosgeldiniz" in msg:                     # kayit basarili
                break
            # kayit basarisizsa (isim alinmis) dongunun basina don, tekrar sor

        except socket.timeout:
            print("[hata] sunucu cevap vermedi, once sunucuyu baslatin.")
            exit(1)
        except ConnectionResetError:
            print("[hata] sunucuya baglanilamadi, once sunucuyu baslatin.")
            exit(1)
        except Exception as e:
            print(f"[hata] Baglanti sirasinda hata olustu: {e}")
            exit(1)

    # ── arka planda dinleyici thread baslat ──
    t = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    t.start()                                        # kullanici yazarken sunucudan gelen mesajlar ekrana duser

    # ── mesaj gonderme dongusu ──
    try:
        while True:
            message = input("> ")                    # kullanicidan girdi al (imlec belirteci eklendi)
            if not message.strip():
                continue                             # bos mesaj gonderilmez
            sock.sendto(message.encode(), (HOST, UDP_PORT))

            if message == "Gorusuruz":              # ayrilma komutu gonderildiyse cik
                print("[bilgi] sohbet odasindan ayrilindi.")
                break
    except (KeyboardInterrupt, EOFError):
        print("\n[bilgi] cikiliyor...")
        sock.sendto("Gorusuruz".encode(), (HOST, UDP_PORT))  # sunucuya ayrilma komutu gonder
    finally:
        sock.close()