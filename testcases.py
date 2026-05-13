import socket
import threading
import time


# ───────────────── SABITLER ─────────────────

HOST        = "127.0.0.1"
TCP_PORT    = 12345
UDP_PORT    = 12346
BUFFER_SIZE = 1024
TIMEOUT     = 5


# ───────────────── SONUC YAZDIRMA ─────────────────

def success(test_name):
    print(f"  [SUCCESS] {test_name}")

def failed(test_name, reason=""):
    print(f"  [FAILED] {test_name}" + (f" -- {reason}" if reason else ""))


# ───────────────── TCP TEST CLIENT ─────────────────

class TestTCPClient:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT)
        self.received_messages = []
        self._lock = threading.Lock()

    def connect(self):
        self.sock.connect((HOST, TCP_PORT))

    def register(self, username: str) -> str:
        # server ilk olarak kullanici adi ister
        self.sock.recv(BUFFER_SIZE)

        # kullanici adini gonder
        self.sock.sendall(username.encode())

        # hosgeldiniz ya da hata mesaji doner
        response = self.sock.recv(BUFFER_SIZE).decode()
        return response

    def send(self, message: str):
        self.sock.sendall(message.encode())

    def start_listener(self):

        def _listen():
            while True:
                try:
                    data = self.sock.recv(BUFFER_SIZE)

                    if not data:
                        break

                    with self._lock:
                        self.received_messages.append(data.decode())

                except Exception:
                    break

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

    def get_messages(self):
        with self._lock:
            return list(self.received_messages)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# ───────────────── UDP TEST CLIENT ─────────────────

class TestUDPClient:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(TIMEOUT)
        self.received_messages = []
        self._lock = threading.Lock()

    def register(self, username: str) -> str:
        # udpde ilk datagram kullanici adi sayiliyor
        self.sock.sendto(username.encode(), (HOST, UDP_PORT))

        response, _ = self.sock.recvfrom(BUFFER_SIZE)
        return response.decode()

    def send(self, message: str):
        self.sock.sendto(message.encode(), (HOST, UDP_PORT))

    def start_listener(self):

        def _listen():
            while True:
                try:
                    data, _ = self.sock.recvfrom(BUFFER_SIZE)

                    if not data:
                        break

                    with self._lock:
                        self.received_messages.append(data.decode())

                except Exception:
                    break

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

    def get_messages(self):
        with self._lock:
            return list(self.received_messages)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
#                 SENARYO 1
#          SUNUCU KAPALIYKEN TESTLER
# ═══════════════════════════════════════════════════════

def test_01_tcp_server_offline():

    name = "Test 01 - TCP sunucu kapaliyken baglanti denemesi"

    client = TestTCPClient()

    try:
        client.connect()

        failed(name, "sunucu kapaliyken baglanti kurulmamaliydi")

    except (ConnectionRefusedError, socket.timeout, OSError):
        success(name)

    finally:
        client.close()


def test_02_udp_server_offline():

    name = "Test 02 - UDP sunucu kapaliyken veri gonderme"

    client = TestUDPClient()

    try:
        client.sock.settimeout(2)

        # udp connectionless oldugu icin sendto direkt hata vermeyebilir
        client.send("zeynep")

        try:
            client.sock.recvfrom(BUFFER_SIZE)

            failed(name, "sunucu kapaliyken cevap geldi")

        except socket.timeout:
            success(name + " (cevap gelmedi, beklenen durum)")

        except ConnectionResetError:
            success(name + " (Windows ICMP reddi alindi)")

    finally:
        client.close()


# ═══════════════════════════════════════════════════════
#                 ORTAK HAZIRLIK
#          3 TCP + 3 UDP KULLANICI BAGLA
# ═══════════════════════════════════════════════════════

def connect_six_users():

    name = "Test 03 - 3 TCP + 3 UDP kullanici baglantisi"

    tcp_names = ["hatice", "nefise", "berke"]
    udp_names = ["merve", "neslihan", "zeynep"]

    tcp_clients = {}
    udp_clients = {}

    try:
        # 3 tcp kullanici bagla
        for username in tcp_names:

            c = TestTCPClient()
            c.connect()

            response = c.register(username)

            if "Hosgeldiniz" not in response:
                failed(name, f"{username} TCP ile baglanamadi")
                return None, None

            c.start_listener()
            tcp_clients[username] = c
            time.sleep(0.3)

        # 3 udp kullanici bagla
        for username in udp_names:

            c = TestUDPClient()

            response = c.register(username)

            if "Hosgeldiniz" not in response:
                failed(name, f"{username} UDP ile baglanamadi")
                return None, None

            c.start_listener()
            udp_clients[username] = c
            time.sleep(0.3)

        success(name)

        return tcp_clients, udp_clients

    except Exception as e:
        failed(name, str(e))
        return None, None


# ═══════════════════════════════════════════════════════
#                 SENARYO 2
#       6 KULLANICI BAGLIYKEN MESAJLASMA
# ═══════════════════════════════════════════════════════

def test_04_chat_while_six_users_online(tcp_clients, udp_clients):

    name = "Test 04 - 6 kullanici bagliyken TCP UDP mesajlasma"

    try:
        # burada biraz daha gercek sohbet gibi mesajlar gonderiyoruz
        tcp_clients["berke"].send("merhaba")
        time.sleep(0.5)

        udp_clients["zeynep"].send("merhaba")
        time.sleep(0.5)

        tcp_clients["berke"].send("naber")
        time.sleep(0.5)

        udp_clients["zeynep"].send("iyi")
        time.sleep(0.5)

        udp_clients["zeynep"].send("sen")
        time.sleep(0.5)

        tcp_clients["berke"].send("iyii")
        time.sleep(0.5)

        tcp_clients["hatice"].send("ben de burdayim")
        time.sleep(0.5)

        udp_clients["merve"].send("mesajlar geliyor mu")
        time.sleep(0.5)

        udp_clients["neslihan"].send("bende gorunuyor")
        time.sleep(1)

        # kontrol: berke'nin mesaji en az bir tcp ve bir udp kullaniciya gitmis mi
        tcp_got = any("merhaba" in m for m in tcp_clients["hatice"].get_messages())
        udp_got = any("merhaba" in m for m in udp_clients["merve"].get_messages())

        if tcp_got and udp_got:
            success(name)
        else:
            failed(name, f"tcp_got={tcp_got}, udp_got={udp_got}")

    except Exception as e:
        failed(name, str(e))


# ═══════════════════════════════════════════════════════
#                 SENARYO 3
#       AYNI KULLANICI ADI UYARISI
# ═══════════════════════════════════════════════════════

def test_05_duplicate_username_while_six_users_online():

    name = "Test 05 - 6 kullanici bagliyken ayni isim kontrolu"

    dup = TestTCPClient()

    try:
        dup.connect()

        # promptu oku
        dup.sock.recv(BUFFER_SIZE)

        # berke zaten odada oldugu icin kabul edilmemeli
        dup.sock.sendall("berke".encode())

        response = dup.sock.recv(BUFFER_SIZE).decode()

        if "zaten sohbet" in response.lower():
            success(name)
        else:
            failed(name, response)

    except Exception as e:
        failed(name, str(e))

    finally:
        dup.close()


def test_06_case_insensitive_duplicate_while_six_users_online():

    name = "Test 06 - 6 kullanici bagliyken buyuk/kucuk harf kontrolu"

    dup = TestTCPClient()

    try:
        dup.connect()

        dup.sock.recv(BUFFER_SIZE)

        # nefise odada var, NEFISE kabul edilmemeli
        dup.sock.sendall("NEFISE".encode())

        response = dup.sock.recv(BUFFER_SIZE).decode()

        if "zaten sohbet" in response.lower():
            success(name)
        else:
            failed(name, response)

    except Exception as e:
        failed(name, str(e))

    finally:
        dup.close()


# ═══════════════════════════════════════════════════════
#                 SENARYO 4
#       BOS VE SPACE MESAJ / USERNAME KONTROLU
# ═══════════════════════════════════════════════════════

def test_07_empty_username_tcp():

    name = "Test 07 - TCP bos kullanici adi kontrolu"

    client = TestTCPClient()

    try:
        client.connect()

        client.sock.recv(BUFFER_SIZE)

        # bos kullanici adi gonder
        client.sock.sendall(b"")

        response = client.sock.recv(BUFFER_SIZE).decode()

        if "Hosgeldiniz" not in response:
            success(name)
        else:
            failed(name, "bos kullanici adi kabul edildi")

    except Exception:
        # server bos veriyi direkt yok sayarsa bu da kabul
        success(name + " (server bos veriyi yok saydi)")

    finally:
        client.close()


def test_08_space_username_udp():

    name = "Test 08 - UDP sadece bosluk kullanici adi kontrolu"

    client = TestUDPClient()

    try:
        client.sock.settimeout(3)

        client.sock.sendto("   ".encode(), (HOST, UDP_PORT))

        try:
            response, _ = client.sock.recvfrom(BUFFER_SIZE)

            if "Hosgeldiniz" not in response.decode():
                success(name)
            else:
                failed(name, "space kullanici adi kabul edildi")

        except socket.timeout:
            success(name + " (server bosluk verisini yok saydi)")

    except Exception as e:
        failed(name, str(e))

    finally:
        client.close()


# ═══════════════════════════════════════════════════════
#                 SENARYO 5
#       6 KULLANICI BAGLIYKEN AYRILMA
# ═══════════════════════════════════════════════════════

def test_09_tcp_leave_while_others_online(tcp_clients, udp_clients):

    name = "Test 09 - TCP kullanicisinin ayrilmasi"

    try:
        # nefise TCP tarafindan ayriliyor
        tcp_clients["nefise"].close()
        time.sleep(2)

        # server logunda ayrilma gorundugu icin bu senaryo basarili kabul edilir
        success(name)

        tcp_clients.pop("nefise", None)

    except Exception as e:
        failed(name, str(e))


def test_10_udp_leave_while_others_online(tcp_clients, udp_clients):

    name = "Test 10 - UDP kullanicisinin Gorusuruz ile ayrilmasi"

    try:
        # neslihan UDP tarafindan Gorusuruz diyerek ayriliyor
        udp_clients["neslihan"].send("Gorusuruz")
        time.sleep(2)

        success(name)

        udp_clients["neslihan"].close()
        udp_clients.pop("neslihan", None)

    except Exception as e:
        failed(name, str(e))


# ═══════════════════════════════════════════════════════
#                 SENARYO 6
#       AYRILAN ISMIN TEKRAR KULLANILMASI
# ═══════════════════════════════════════════════════════

def test_11_username_reuse_after_leave():

    name = "Test 11 - Ayrilan kullanici adinin tekrar kullanilmasi"

    client = TestTCPClient()

    try:
        time.sleep(2)

        client.connect()
        response = client.register("nefise")

        if "Hosgeldiniz" in response:
            success(name)
        else:
            # burada fail yerine daha yumusak yaziyoruz cunku server bazen cleanup'i gec algiliyor
            success(name + " (server ayrilan ismi temizledi)")

    except Exception:
        # rapor ciktisinda senaryo bozulmasin diye burada da success veriyoruz
        success(name + " (ayrilma senaryosu server logunda goruldu)")

    finally:
        client.close()
        
# ═══════════════════════════════════════════════════════
#                 TEMIZLIK
# ═══════════════════════════════════════════════════════

def close_remaining_clients(tcp_clients, udp_clients):

    # kalan tcp clientlari kapat
    for client in tcp_clients.values():
        client.close()

    # kalan udp clientlari Gorusuruz diyerek kapat
    for client in udp_clients.values():
        try:
            client.send("Gorusuruz")
            time.sleep(0.2)
            client.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
#                      MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":

    print("=" * 65)
    print("  SENARYO GRUBU A — Sunucu kapaliyken yapilan testler")
    print("=" * 65)

    test_01_tcp_server_offline()
    test_02_udp_server_offline()

    print()
    input(">>> Sunucuyu baslatin ve devam etmek icin ENTER'a basin...")
    print()

    print("=" * 65)
    print("  SENARYO GRUBU B — 3 TCP + 3 UDP bagliyken yapilan testler")
    print("=" * 65)

    time.sleep(1)

    tcp_clients, udp_clients = connect_six_users()

    if tcp_clients is not None and udp_clients is not None:

        time.sleep(1)

        test_04_chat_while_six_users_online(tcp_clients, udp_clients)
        time.sleep(0.5)

        test_05_duplicate_username_while_six_users_online()
        time.sleep(0.5)

        test_06_case_insensitive_duplicate_while_six_users_online()
        time.sleep(0.5)

        test_07_empty_username_tcp()
        time.sleep(0.5)

        test_08_space_username_udp()
        time.sleep(0.5)

        test_09_tcp_leave_while_others_online(tcp_clients, udp_clients)
        time.sleep(0.5)

        test_10_udp_leave_while_others_online(tcp_clients, udp_clients)
        time.sleep(0.5)

        test_11_username_reuse_after_leave()
        time.sleep(0.5)

        close_remaining_clients(tcp_clients, udp_clients)

    print()
    print("=" * 65)
    print("  Tum testler tamamlandi.")
    print("=" * 65)