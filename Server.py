import socket
import threading


# ───────────────── SABITLER VE GLOBAL DEGISKENLER ────────────────

HOST        = "127.0.0.1"    # sunucunun dinleyeceği IP adresi
TCP_PORT    = 12345          # TCP baglantıları icin port numarası
UDP_PORT    = 12346          # UDP datagramları icin port numarası
BUFFER_SIZE = 1024

# aktif TCP istemcilerini tutan sozluk: { kullanıcı_adı : socket_nesnesi }
tcp_clients = {}

# Aktif UDP istemcilerini tutan sozluk: { kullanıcı_adı : (ip, port) }
# UDP'de kalıcı baglantı olmadıgından adres bilgisi saklanır
udp_clients = {}

# veri butunlugunu korumak icin kilit kullanılır
lock = threading.Lock()

# UDP yanıtları gondermek icin sunucu tarafında tek bir soket yeterlidir
udp_server_socket = None


# ─────────────────────────── BROADCAST ───────────────────────────

def broadcast(message: str, exclude_username: str = None):
    """
    sohbet odasina gonderilen mesajin, gonderen haric tum istemcilere iletilmesini saglar
    """
    if not message.strip():                 # bos mesaj ya da bosluk kabul edilmez
        return

    encoded = message.encode()              # mesaj gonderime hazir hale getirilir, her seferinde tekrar encode edilmez

    with lock:      # tum client'lara aynı anda erisilmesi gerektiginden lock alinir

        # ── TCP istemcilerine gonderim ──
        for username, client_sock in list(tcp_clients.items()):
            if username == exclude_username:   # mesaji gonderen kisi atlanir
                continue
            try:
                client_sock.sendall(encoded)   # tum veriyi gonderir
            except Exception:
                pass       # erisilemeyen tcp atlanir

        # ── UDP istemcilerine gonderim ──
        for username, addr in list(udp_clients.items()):
            if username == exclude_username:
                continue
            try:
                udp_server_socket.sendto(encoded, addr)   # UDP'de baglanti olmadigindan adres belirtilir
            except Exception:
                pass        # erisilemeyen UDP atlanir


# ──────────────────────── USERNAME EXISTS ────────────────────────

def username_exists(name: str) -> bool:
    """
    ayni kullanici adinin TCP ve UDP istemcileri arasinda tekrar
    kullanilmasini onler. karsilastirma buyuk/kucuk harf duyarsizdir
    !!! bu fonksiyon her zaman lock alinmis bir blok icinden cagrilmalidir !!!
    """
    name_lower = name.lower()

    for u in list(tcp_clients.keys()) + list(udp_clients.keys()):
        if u.lower() == name_lower:
            return True

    return False


# ─────────────────────── TCP CLIENT HANDLE ───────────────────────

def handle_tcp_client(client_sock: socket.socket, addr):
    """
    her yeni TCP baglantisi icin tcp_listener() tarafindan ayri bir
    thread'de baslatilir. Kullanici adi dogrulama, mesajlasma ve
    ayrilma islemlerini sirasiyla yonetir.
    """
    username = None
    try:

        # ── ASAMA 1: kullanici adi dogrulama ──
        client_sock.sendall("Kullanıcı adınızı giriniz: ".encode())   # sunucu istemciden kullanici adi talep eder

        while True:                                 # uygun bir username girilmesini garanti altina alir
            data = client_sock.recv(BUFFER_SIZE)    # istemci cevabini oku
            if not data:
                return                              # istemci baglantiyi kapatirsa bos veri doner -> fonksiyondan cik

            candidate = data.decode().strip()       # veriyi stringe cevir ve strip et

            if not candidate:                       # bos mesaj ya da bosluk kabul edilmez
                client_sock.sendall("Kullanıcı adı boş olamaz, tekrar giriniz: ".encode())
                continue

            with lock:                              # tcp_clients ve udp_clients'a guvenli erisim icin kilit alindi
                if username_exists(candidate):      # isim alinmis mi, alindiysa dongunun basina don
                    client_sock.sendall("Bu kullanıcı zaten sohbet odasında, lütfen başka bir kullanıcı adı giriniz!\n".encode())
                    continue 

                username = candidate                    # isim alinmamis, kaydet
                tcp_clients[username] = client_sock     # soket referansi saklanir

            break   # kayit tamamlandi, donguden cik

        # ── ASAMA 2: hosgeldin & katilma duyurusu ──
        client_sock.sendall(f"Hosgeldiniz {username}, [TCP] ile baglisiniz!\n".encode())  # yalnizca baglanan istemciye

        join_msg = f"{username} - [TCP] sohbet odasina katildi."
        print(join_msg)                                 # sunucu konsoluna yaz
        broadcast(join_msg, exclude_username=username)  # diger tum istemcilere duyur

        # ── ASAMA 3: mesajlasma dongusu ──
        while True:
            data = client_sock.recv(BUFFER_SIZE)        # istemciden mesaj bekle
            if not data:
                break                                   # baglanti kapandi

            message = data.decode().strip()
            if not message:
                continue                                # bos mesaj yayinlanmaz

            full_msg = f"{username}[TCP] : {message}"
            print(full_msg)
            broadcast(full_msg, exclude_username=username)

    except Exception as e:
        print(f"[hata] TCP istemci ({addr}): {e}")

    finally:
        # ── ASAMA 4: ayrilma & temizlik ──
        # try blogu hangi yolla cikarsa ciksın bu blok her zaman calisir
        if username:
            with lock:
                tcp_clients.pop(username, None)     # sozlukten guvenli sekilde kaldir
            leave_msg = f"{username} - [TCP] sohbet odasindan ayrildi."
            print(leave_msg)
            broadcast(leave_msg)                    # gonderen artik listede yok
        try:
            client_sock.close()
        except Exception:
            pass                                    # soket zaten kapaliys hata firlatmasin


# ──────────────────────── TCP LISTENER ───────────────────────────

def tcp_listener():
    """
    gelen TCP baglantilarini kabul eder
    her baglanti icin ayri bir handle_tcp_client thread'i baslatir
    boylece bir istemcinin islemi digerlerini bloke etmez
    """
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # sunucu yeniden baslatilirken port dolu hatasini onle
    tcp_sock.bind((HOST, TCP_PORT))
    tcp_sock.listen()
    print(f"[TCP] {HOST}:{TCP_PORT} uzerinde dinleniyor...")

    while True:
        client_sock, addr = tcp_sock.accept()       # yeni baglanti gelene kadar bekle
        print(f"[TCP] yeni baglanti: {addr}")
        t = threading.Thread(target=handle_tcp_client, args=(client_sock, addr), daemon=True)
        t.start()                                   # her istemci icin bagimsiz thread, ana dongu bloke olmaz


# ──────────────────────── UDP LISTENER ───────────────────────────

def udp_listener():
    """
    tum UDP datagramlarini tek thread'de isler.
    ilk datagram    -> kullanici adi kaydi
    'Gorusuruz'     -> ayrilma komutu
    digerleri       -> broadcast
    addr_to_user sozlugu ile adres-kullanici eslesmesi tutulur.
    """
    global udp_server_socket                        # broadcast() tarafindan da kullanilacagindan global tanimlanir

    udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server_socket.bind((HOST, UDP_PORT))
    print(f"[UDP] {HOST}:{UDP_PORT} uzerinde dinleniyor...")

    # { (ip, port): username } — udp_clients'in ters eslemesi
    # gelen datagramin hangi kullanicidan geldigi O(1) ile bulunur
    addr_to_user = {}

    while True:
        try:
            data, addr = udp_server_socket.recvfrom(BUFFER_SIZE)    # datagram al, gonderen adresi doner
        except Exception as e:
            print(f"[hata] UDP alim: {e}")
            continue                                # hatali datagrami atla, dinlemeye devam et

        message = data.decode().strip()
        if not message:
            continue                                # bos datagram yok sayilir

        # ── kayitli kullanici: mesajlasma modu ──
        if addr in addr_to_user:
            username = addr_to_user[addr]           # adrese karsilik gelen kullanici adini al

            if message == "Gorusuruz":              # ayrilma komutu
                with lock:
                    udp_clients.pop(username, None)
                addr_to_user.pop(addr, None)        # adres -> isim eslemesini de kaldir
                leave_msg = f"{username} - [UDP] sohbet odasindan ayrildi."
                print(leave_msg)
                broadcast(leave_msg)
                continue

            full_msg = f"{username}[UDP] : {message}"
            print(full_msg)
            broadcast(full_msg, exclude_username=username)

        # ── yeni adres: ilk datagram = kullanici adi ──
        else:
            candidate = message                     # ilk datagram icerigi kullanici adi adayidir

            with lock:                              # kayit sirasinda listeler degismesin diye kilit al
                if username_exists(candidate):
                    udp_server_socket.sendto(
                        "Bu kullanici zaten sohbet odasinda, lutfen baska bir kullanici adi giriniz!\n".encode(),
                        addr
                    )
                    continue                        # addr_to_user'a eklenmez, istemci tekrar dener

                udp_clients[candidate] = addr
                addr_to_user[addr] = candidate

            udp_server_socket.sendto(
                f"Hosgeldiniz {candidate}, [UDP] ile baglisiniz!\n".encode(),
                addr
            )
            join_msg = f"{candidate} - [UDP] sohbet odasina katildi."
            print(join_msg)
            broadcast(join_msg, exclude_username=candidate)


# ──────────────────────────── MAIN ───────────────────────────────

if __name__ == "__main__":
    print("=== sohbet odasi sunucusu baslatiliyor ===")

    t_tcp = threading.Thread(target=tcp_listener, daemon=True)
    t_udp = threading.Thread(target=udp_listener, daemon=True)

    t_tcp.start()
    t_udp.start()

    print("sunucu calisiyor. cikmak icin ctrl+c.\n")
    try:
        t_tcp.join()                                # ana thread burada bekler; sunucu kapanmaz
        t_udp.join()
    except KeyboardInterrupt:
        print("\n[sunucu] kapatiliyor...")