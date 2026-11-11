"""Dataset uji router: (query, intent yang diharapkan, ticket_id yang diharapkan)."""

CASES = [
    ("berapa jatah cuti tahunan saya?", "faq", None),
    ("bagaimana cara reset password VPN?", "faq", None),
    ("apakah ada kebijakan kerja hybrid?", "faq", None),
    ("laptop saya rusak harus bagaimana?", "faq", None),
    ("gimana cara dapat akses Google Workspace", "faq", None),
    ("aplikasi apa yang dipakai untuk komunikasi tim?", "faq", None),
    ("bagaimana cara membuat tiket baru ke tim IT?", "faq", None),
    ("cuaca di Jakarta besok gimana?", "faq", None),
    ("apa status TICKET-0042 saya?", "ticket_status", "TICKET-0042"),
    ("tolong cek TICKET-0002", "ticket_status", "TICKET-0002"),
    ("ticket-7 udah sampai mana ya", "ticket_status", "TICKET-0007"),
    ("update terakhir untuk tiket 0015 dong", "ticket_status", "TICKET-0015"),
    ("TICKET-9999 statusnya apa?", "ticket_status", "TICKET-9999"),
    ("Mau tanya progres tiket TICKET-0005 soal VPN", "ticket_status", "TICKET-0005"),
    ("cek status tiket saya dong", "ticket_status", None),  # tanpa nomor -> router minta nomor tiket
    # Kasus sulit yang sengaja dimasukkan
    ("permintaan akses saya sudah diproses belum?", "ticket_status", None),  # tidak menyebut kata 'tiket'
    ("kenapa tiket saya belum dibalas 3 hari?", "ticket_status", None),
]
