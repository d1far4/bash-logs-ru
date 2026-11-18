"""Генератор учебных данных: data/access.log, data/app.log, data/orders.csv.

Запуск:  python gen_data.py
Нужен только Python 3.8+ (стандартная библиотека). Результат детерминирован:
используется собственный генератор псевдослучайных чисел с фиксированным
зерном, поэтому файлы одинаковы на любой версии Python и в любой ОС.
Файлы пишутся в UTF-8 с переводами строк LF.
"""
from pathlib import Path

SEED = 20260314
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
M64 = 0xFFFFFFFFFFFFFFFF


class Rng:
    """xorshift64*: маленький детерминированный генератор."""

    def __init__(self, seed):
        self.s = (seed * 2685821657736338717 + 1442695040888963407) & M64 or 1

    def next(self):
        x = self.s
        x ^= x >> 12
        x ^= (x << 25) & M64
        x ^= x >> 27
        self.s = x
        return (x * 0x2545F4914F6CDD1D) & M64

    def below(self, n):
        return (self.next() >> 11) % n

    def randint(self, a, b):
        return a + self.below(b - a + 1)

    def choice(self, seq):
        return seq[self.below(len(seq))]

    def shuffle(self, items):
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]

    def weighted(self, pairs):
        total = sum(w for _, w in pairs)
        r = self.below(total)
        for item, w in pairs:
            if r < w:
                return item
            r -= w
        raise AssertionError


def write_lines(name, lines):
    DATA.mkdir(exist_ok=True)
    with open(DATA / name, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")


# --------------------------------------------------------------------------
# access.log: nginx "combined", книжный интернет-магазин, 14 марта 2026
# --------------------------------------------------------------------------

HOURS = [2, 1, 1, 2, 1, 1, 2, 4, 5, 8, 7, 8, 11, 9, 6, 5, 5, 6, 7, 8, 9, 7, 3, 2]
STATUSES = {200: 95, 301: 6, 304: 6, 404: 7, 500: 3, 502: 3}

HEAVY = [  # (ip, число запросов, номер браузера)
    ("203.0.113.7", 15, 6),
    ("198.51.100.23", 15, 0),
    ("192.0.2.44", 10, 1),
    ("203.0.113.58", 8, 3),
    ("192.0.2.101", 8, 2),
    ("198.51.100.9", 8, 4),
]
BOTS = [  # (ip, число запросов, User-Agent)
    ("198.51.100.200", 6,
     "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("203.0.113.201", 4,
     "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
    ("192.0.2.202", 3,
     "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"),
    ("192.0.2.203", 2, "Mozilla/5.0 (compatible; AhrefsBot/7.0)"),
]
BROWSERS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 YaBrowser/24.1 Safari/537.36",
    "python-requests/2.31.0",
]
REFERERS = ["-", "-", "-", "-", "-", "-", "https://www.google.com/",
            "https://yandex.ru/", "https://www.example.com/catalog"]

SLUGS = ["war-and-peace", "the-master-and-margarita", "python-for-beginners",
         "the-hobbit", "dune", "crime-and-punishment", "sql-in-10-minutes",
         "bash-cookbook", "metro-2033", "little-prince"]
TERMS = ["python", "tolstoy", "fantasy", "bash", "dune", "детектив"]

PATHS_200 = (
    [("/", 10), ("/catalog", 12), ("/catalog?page=2", 5), ("/catalog?page=3", 3),
     ("/catalog?sort=price", 4), ("/cart", 5), ("/checkout", 3), ("/delivery", 2),
     ("/about", 2), ("/login", 3), ("/static/css/main.css", 6),
     ("/static/js/app.js", 5), ("/favicon.ico", 3)]
    + [("/book/" + s, 3) for s in SLUGS]
    + [("/book/%s?utm_source=email" % s, 1) for s in SLUGS[:4]]
    + [("/search?q=" + t, 1) for t in TERMS]
)
PATHS_BOT = ["/robots.txt", "/sitemap.xml", "/", "/catalog", "/catalog?page=2",
             "/catalog?page=3", "/book/dune", "/book/the-hobbit"]
PATHS_301 = ["/old-catalog", "/index.php", "/catalog/", "/book/dune/", "/books"]
PATHS_304 = ["/static/css/main.css", "/static/js/app.js", "/catalog", "/book/war-and-peace"]
PATHS_404 = ["/wp-login.php", "/admin", "/book/missing-title", "/img/cover-999.jpg", "/.env"]
REQ_500 = ["POST /cart", "POST /checkout", "POST /cart"]
REQ_502 = ["POST /login", "GET /api/orders", "GET /checkout"]


def pick_bytes(rng, status, path):
    if status == 304:
        return "-"
    if status == 301:
        return str(rng.choice([169, 178]))
    if status == 404:
        return str(rng.choice([146, 153, 612]))
    if status == 500:
        return str(rng.choice([177, 552]))
    if status == 502:
        return str(rng.choice([150, 166]))
    if path.endswith(".css"):
        return str(rng.randint(14000, 19000))
    if path.endswith(".js"):
        return str(rng.randint(38000, 47000))
    if path.endswith(".ico"):
        return "1150"
    if path.endswith(".txt") or path.endswith(".xml"):
        return str(rng.randint(180, 900))
    return str(rng.randint(2100, 31000))


def make_access_log():
    rng = Rng(SEED)
    n = sum(HOURS)
    assert n == sum(STATUSES.values()) == 120

    # время: по часам, внутри часа по возрастанию
    times = []
    for h, cnt in enumerate(HOURS):
        stamps = sorted((rng.randint(0, 59), rng.randint(0, 59)) for _ in range(cnt))
        times += ["%02d:%02d:%02d" % (h, m, s) for m, s in stamps]

    # IP-адреса: тяжёлые, боты и «редкие» посетители
    ips = []  # (ip, user_agent)
    for ip, cnt, b in HEAVY:
        ips += [(ip, BROWSERS[b])] * cnt
    for ip, cnt, ua in BOTS:
        ips += [(ip, ua)] * cnt
    taken = {ip for ip, _, _ in HEAVY} | {ip for ip, _, _ in BOTS}
    pool = []
    prefixes = ["192.0.2.", "198.51.100.", "203.0.113."]
    while len(pool) < 22:
        ip = rng.choice(prefixes) + str(rng.randint(2, 99))
        if ip not in taken:
            taken.add(ip)
            pool.append((ip, BROWSERS[rng.below(len(BROWSERS) - 1)]))
    cnts = [1] * 22
    for _ in range(n - len(ips) - 22):
        while True:
            i = rng.below(22)
            if cnts[i] < 3:
                cnts[i] += 1
                break
    for (ip, ua), c in zip(pool, cnts):
        ips += [(ip, ua)] * c
    assert len(ips) == n
    rng.shuffle(ips)

    statuses = []
    for st, cnt in STATUSES.items():
        statuses += [st] * cnt
    rng.shuffle(statuses)

    recs = []
    c500 = c502 = 0
    for i in range(n):
        ip, ua = ips[i]
        st = statuses[i]
        is_bot = "bot" in ua.lower()
        method = "GET"
        if st == 200:
            path = rng.choice(PATHS_BOT) if is_bot else rng.weighted(PATHS_200)
        elif st == 301:
            path = rng.choice(PATHS_301)
        elif st == 304:
            path = rng.choice(PATHS_304)
        elif st == 404:
            path = rng.choice(PATHS_404)
        elif st == 500:
            method, path = REQ_500[c500].split()
            c500 += 1
        else:
            method, path = REQ_502[c502].split()
            c502 += 1
        ref = "-" if is_bot else rng.choice(REFERERS)
        recs.append(dict(ip=ip, ua=ua, st=st, method=method, path=path, ref=ref,
                         bytes=None, time=times[i], bot=is_bot))

    # несколько POST среди успешных ответов
    ok_human = [r for r in recs if r["st"] == 200 and not r["bot"]]
    for k, (method, path) in enumerate([("POST", "/login")] * 4 + [("POST", "/cart")] * 3):
        r = ok_human[k * 7 + 2]
        r["method"], r["path"], r["ref"] = method, path, "-"

    # ловушки для grep 500: «500» в пути, в размере ответа, в 404
    ok_human = [r for r in recs if r["st"] == 200 and not r["bot"]
                and r["method"] == "GET" and r["path"].startswith("/book/")]
    ok_human[1]["path"] = "/book/500-russian-proverbs"
    ok_human[3]["bytes"] = "12500"
    ok_human[5]["bytes"] = "25001"
    r404 = [r for r in recs if r["st"] == 404]
    r404[1]["path"] = "/book/500-missing"

    # человеческие запросы со словом «bot» в пути (а не в User-Agent)
    pages = [r for r in recs if r["st"] == 200 and not r["bot"]
             and r["method"] == "GET" and r["path"] in ("/catalog", "/", "/delivery", "/about", "/cart")]
    for r in pages[:3]:
        r["path"] = "/book/robotics-for-beginners"

    lines = []
    for r in recs:
        b = r["bytes"] or pick_bytes(rng, r["st"], r["path"])
        lines.append(
            '%s - - [14/Mar/2026:%s +0300] "%s %s HTTP/1.1" %d %s "%s" "%s"'
            % (r["ip"], r["time"], r["method"], r["path"], r["st"], b, r["ref"], r["ua"])
        )
    return lines


# --------------------------------------------------------------------------
# app.log: журнал приложения
# --------------------------------------------------------------------------

APP_LOG = [
    ("00:00:03", "INFO", "catalog", "reindex started items=1840"),
    ("00:00:07", "DEBUG", "catalog", "reindex batch=1 took=312ms"),
    ("00:00:11", "INFO", "catalog", "reindex finished items=1840 took=4210ms"),
    ("03:30:00", "INFO", "mailer", "daily digest queued recipients=212"),
    ("03:30:05", "DEBUG", "mailer", "smtp connect took=88ms"),
    ("07:02:15", "INFO", "auth", "login ok user=u1042"),
    ("08:12:40", "WARN", "auth", "failed login attempts=3 ip=203.0.113.7"),
    ("08:12:41", "INFO", "orders", "order created order=10430 items=2"),
    ("08:12:42", "INFO", "payment", "charge started order=10430 amount=1890"),
    ("08:12:43", "DEBUG", "payment", "gateway request order=10430 took=845ms"),
    ("08:12:44", "INFO", "payment", "charge ok order=10430 took=870ms"),
    ("09:15:02", "INFO", "orders", "order created order=10435 items=1"),
    ("09:15:03", "INFO", "payment", "charge started order=10435 amount=540"),
    ("09:15:04", "INFO", "payment", "charge ok order=10435 took=612ms"),
    ("09:47:30", "DEBUG", "catalog", "query category=fiction took=14ms"),
    ("09:47:31", "DEBUG", "catalog", "query category=science took=23ms"),
    ("10:05:11", "INFO", "orders", "order created order=10438 items=4"),
    ("10:05:12", "INFO", "payment", "charge started order=10438 amount=4120"),
    ("10:05:42", "ERROR", "payment", "charge failed order=10438 reason=gateway_timeout took=30004ms"),
    ("10:05:43", "INFO", "payment", "retry scheduled order=10438 after ERROR from gateway"),
    ("10:07:44", "INFO", "payment", "retry charge ok order=10438 took=701ms"),
    ("10:30:00", "WARN", "catalog", "slow query category=history took=1203ms"),
    ("11:20:15", "INFO", "orders", "order created order=10441 items=2"),
    ("11:20:16", "INFO", "payment", "charge started order=10441 amount=2350"),
    ("11:20:17", "ERROR", "payment", "charge declined order=10441 reason=insufficient_funds took=530ms"),
    ("11:20:18", "WARN", "orders", "order=10441 moved to status=cancelled"),
    ("12:02:09", "DEBUG", "auth", "session refreshed user=u0877"),
    ("12:15:33", "INFO", "orders", "order created order=10443 items=1"),
    ("12:15:34", "INFO", "payment", "charge started order=10443 amount=990"),
    ("12:15:35", "ERROR", "orders", "order=10443 not confirmed: payment service returned 502"),
    ("12:15:36", "ERROR", "payment", "charge failed order=10443 reason=bad_gateway took=2010ms"),
    ("12:40:00", "INFO", "mailer", "receipt sent order=10435 took=154ms"),
    ("13:05:21", "WARN", "orders", "cannot parse order=n/a in callback from partner"),
    ("13:44:10", "INFO", "orders", "order created order=10445 items=3"),
    ("13:44:11", "INFO", "payment", "charge ok order=10445 took=498ms"),
    ("14:10:55", "ERROR", "mailer", "cannot send payment receipt order=10445 smtp=451 took=3002ms"),
    ("14:11:30", "INFO", "mailer", "receipt resent order=10445 took=190ms"),
    ("15:00:00", "INFO", "catalog", "price update items=212"),
    ("15:00:02", "DEBUG", "catalog", "price update took=1850ms"),
    ("15:30:12", "INFO", "orders", "order created order=10447 items=2"),
    ("15:30:13", "INFO", "payment", "charge started order=10447 amount=3100"),
    ("15:30:15", "ERROR", "payment", "charge failed order=10447 reason=card_expired took=640ms"),
    ("16:22:08", "INFO", "auth", "login ok user=u0123"),
    ("17:01:45", "INFO", "orders", "order created order=10449 items=1"),
    ("17:01:46", "WARN", "orders", "merge duplicate order=10449 into order=10448"),
    ("17:01:47", "ERROR", "orders", "order=10449 stuck in status=pending_payment"),
    ("17:30:00", "DEBUG", "payment", "reconcile batch took=120ms"),
    ("18:12:12", "INFO", "orders", "order created order=10450 items=2"),
    ("18:12:13", "INFO", "payment", "charge ok order=10450 took=733ms"),
    ("19:05:33", "WARN", "auth", "failed login attempts=5 ip=198.51.100.23"),
    ("19:05:50", "ERROR", "auth", "account locked user=u0456 after 5 attempts"),
    ("20:15:02", "INFO", "orders", "order created order=10452 items=5"),
    ("20:15:03", "INFO", "payment", "charge started order=10452 amount=6780"),
    ("20:15:04", "ERROR", "payment", "charge failed order=10452 reason=gateway_error took=1530ms"),
    ("21:00:00", "INFO", "catalog", "cache warmup items=300"),
    ("21:00:05", "DEBUG", "catalog", "cache warmup took=2750ms"),
    ("22:30:41", "WARN", "payment", "gateway latency high took=2210ms"),
    ("23:00:00", "INFO", "mailer", "daily digest sent recipients=212 took=5120ms"),
    ("23:59:58", "INFO", "catalog", "log rotated"),
]


def make_app_log():
    return ["2026-03-14 %s %-5s [%s] %s" % (t, lvl, mod, msg) for t, lvl, mod, msg in APP_LOG]


# --------------------------------------------------------------------------
# orders.csv: выгрузка заказов, разделитель «;», как из русского Excel
# --------------------------------------------------------------------------

CITIES = [("Москва", 9), ("Санкт-Петербург", 6), ("Казань", 5), ("Новосибирск", 4),
          ("Екатеринбург", 4), ("Нижний Новгород", 3), ("Краснодар", 3)]
CUSTOMERS = ["Иванов А.", "Петрова М.", "Сидоров К.", "Кузнецова Е.", "Смирнов Д.",
             "Попова А.", "Васильев И.", "Новикова О.", "Фёдоров П.", "Морозова Н.",
             "Волков С.", "Алексеева Т.", "Лебедев В.", "Козлова Ю.", "Николаев Р."]
FIXED = {  # id -> (город, сумма, статус); согласовано с app.log
    10430: (None, 1890, "paid"),
    10435: (None, 540, "paid"),
    10438: (None, 4120, "paid"),
    10441: (None, 2350, "cancelled"),
    10443: ("Казань", 990, "cancelled"),
    10445: ("", 1450, "paid"),          # город не указан
    10447: ("Новосибирск", 3100, "cancelled"),
    10448: (None, 760, "paid"),
    10449: (None, 2780, "paid"),
    10450: (None, 2200, "paid"),
}


def make_orders():
    rng = Rng(SEED + 1)
    rows = []
    first, last = 10413, 10451
    for oid in range(first, last + 1):
        day = 8 + (oid - first) * 7 // (last - first + 1)
        city, amount, status = FIXED.get(oid, (None, None, None))
        if city is None:
            city = rng.weighted(CITIES)
        if amount is None:
            amount = rng.randint(30, 900) * 10
        if status is None:
            status = rng.weighted([("paid", 24), ("cancelled", 4), ("refunded", 3)])
        rows.append("%d;2026-03-%02d;%s;%s;%d;%s"
                    % (oid, day, city, rng.choice(CUSTOMERS), amount, status))
    # одна строка продублирована: полный дубль заказа 10447 в конце выгрузки
    dup = [r for r in rows if r.startswith("10447;")][0]
    rows.append(dup)
    return ["id;date;city;customer;amount;status"] + rows


def main():
    access = make_access_log()
    write_lines("access.log", access)
    write_lines("app.log", make_app_log())
    write_lines("orders.csv", make_orders())
    print("access.log: %d lines, app.log: %d lines, orders.csv: %d lines"
          % (len(access), len(APP_LOG), len(make_orders())))


if __name__ == "__main__":
    main()
