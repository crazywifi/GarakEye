# ⚡ GarakEye

> **A professional HTML report generator for [Garak](https://github.com/leondz/garak) LLM security scans.**  
> Turn raw `.jsonl` output into a rich, interactive vulnerability report — built for red teamers and AI security researchers.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/LLM_Security-red?style=for-the-badge&logo=shield&logoColor=white"/>
  <img src="https://img.shields.io/badge/Garak-Compatible-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/No_Dependencies-✓-brightgreen?style=for-the-badge"/>
</p>

---

## 🔍 Why GarakEye?

Garak's built-in HTML report is minimal and hard to read during a security assessment. **GarakEye** transforms the raw `.jsonl` scan log into a fully interactive, dark-themed report that actually helps you understand your results:

| Feature | Garak Default | GarakEye |
|---|---|---|
| Per-attempt payload/response view | ❌ | ✅ |
| Injection success highlighting | ❌ | ✅ |
| Per-probe block rate pills | ❌ | ✅ |
| Overall robustness score ring | ❌ | ✅ |
| Attack type / rogue string details | ❌ | ✅ |
| Detection trigger display | ❌ | ✅ |
| Zero dependencies (pure stdlib) | ✅ | ✅ |

---

## 📸 Screenshot

![GarakEye Report Screenshot](screenshot.png)

> *Dark-themed, interactive report with expandable attempt cards, injection highlights, and a robustness score ring.*

---

## 🚀 Quick Start

### Requirements
- Python 3.8+
- A Garak `.jsonl` report file (found in `~/.local/share/garak/` after a scan)

### Install
```bash
git clone https://github.com/crazywifi/garakeye
cd garakeye
```

No pip install needed — GarakEye uses only Python standard library.

### Usage
```bash
# Auto-name output
python garak_report.py my_scan.report.jsonl

# Specify output file
python garak_report.py my_scan.report.jsonl report.html
```

Then open `report.html` in any browser.

---

## 🧪 Running a Garak Scan (Example)

If you haven't run Garak yet, here's a basic example to generate the `.jsonl` file:

```bash
pip install garak

# Scan an OpenAI model for prompt injection
python -m garak -m openai -n gpt-3.5-turbo -p promptinject

# JSONL report is saved at:
# ~/.local/share/garak/<run-id>.report.jsonl
```

Then feed that file to GarakEye:
```bash
python garak_report.py ~/.local/share/garak/<run-id>.report.jsonl
```

---

## 📊 Report Sections

### 🔵 Header & Metadata
Run ID, probe spec, target type, total attempts and generations at a glance.

### 🟡 Robustness Score Ring
Color-coded overall block rate:
- 🟢 Green — ≥ 80% blocked (robust)
- 🟡 Yellow — 50–79% blocked (moderate risk)
- 🔴 Red — < 50% blocked (high risk)

### 🟠 Probe Pills
Each probe shows its individual block rate. Failed probes are highlighted in red.

### 📋 Attempt Cards (expandable)
Click any attempt to expand full details:
- **Attack type** and **rogue string**
- **Injected instruction** payload
- **Detection triggers** that were tested
- **Every conversation** with full payload sent and model response
- Injected strings are **highlighted in red** in the model response

---

## 📁 Project Structure

```
garakeye/
├── garak_report.py   # Main report generator (single file, no deps)
├── README.md
└── screenshot.png    # Example report screenshot
```

---

## 🛠️ Supported Probes

GarakEye correctly parses and renders reports from any Garak probe, including:

- `promptinject.*` (HijackHateHumans, HijackKillHumans, HijackLongPrompt, etc.)
- `dan.*`
- `knownbadsignatures.*`
- `malwaregen.*`
- All other Garak probe families

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/cool-thing`)
3. Commit your changes (`git commit -m 'Add cool thing'`)
4. Push to the branch (`git push origin feature/cool-thing`)
5. Open a Pull Request

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

## 👤 Author

**[crazywifi (LazyHacker)](https://github.com/crazywifi)**  
AI Security Research | Red Teaming | LLM Vulnerability Analysis

---

## ⚠️ Disclaimer

GarakEye is intended for **authorized security testing only**. Always obtain proper permission before scanning any LLM system or API. The author is not responsible for any misuse.

---

<p align="center">Made with ☕ and ⚡ by <a href="https://github.com/crazywifi">crazywifi</a></p>
