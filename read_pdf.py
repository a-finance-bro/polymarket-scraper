from pypdf import PdfReader

reader = PdfReader("jeremywhittaker.com_index.php_2024_09_24_arbitrage-in-polymarket-com_.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"
print(text)
