# ManaSeva — Community Help AI

ManaSeva is a beginner-friendly website for community information. It has a chatbot, private issue reports, links to official Indian government websites, and English and Telugu interface options. It runs on your Windows computer.

## What the demo can do

- Chat with a local Ollama model, when Ollama is available.
- Show simple, clearly labelled offline answers when the model is unavailable.
- Give fixed guidance for scheme and scholarship questions instead of guessing eligibility.
- Reject AI answers containing unverified website addresses or phone numbers.
- Choose a help category: health, education, government schemes, sanitation, public services, or general help.
- Save a community issue to a private SQLite database on this computer.
- Open official emergency, health, scheme, scholarship, government-services, and grievance websites.
- Switch the interface and offline guidance between English and Telugu.

To change the language, use the **Choose language / భాషను ఎంచుకోండి** menu near the top of the page.

## Before you start

- Windows 10 or 11 and Python 3.10 or later.
- An internet connection for installing Streamlit. The app does not require an API key or paid service.
- Ollama is optional. The offline demo still works without it.

This computer already has the Ollama model `gemma3:1b`. It is a small model of about 806 MB, so there is no need to download another model for the demo. Ollama can use that model locally; prompts are sent to the Ollama service on your own computer, not to a paid AI API.

## First-time setup in VS Code

1. Open the `ManaSeva` folder in VS Code: select **File → Open Folder...**, then choose the folder named `ManaSeva`.
2. Select **Terminal → New Terminal**.
3. In the terminal, run these commands one at a time:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

   If Windows says that running scripts is disabled, use this command in that terminal, then activate the environment again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

   This change only lasts until you close this terminal.

## Start the website

With the virtual environment active, run:

```powershell
python -m streamlit run app.py
```

The browser should open at `http://localhost:8501`. To stop the website, click the terminal and press **Ctrl+C**.

## Start or check local AI

Ollama normally starts with Windows. Check that it is available by opening PowerShell and running:

```powershell
ollama list
```

If the list includes `gemma3:1b`, the model is installed. If Ollama is stopped, open the Ollama application from the Windows Start menu. Then refresh the ManaSeva page. If Ollama or the model is unavailable, the app explains this and keeps working with its built-in offline demo. ManaSeva does not download a model.

## Privacy and safety

- Chat history stays in the current browser session and is not written to the issue-report database.
- Issue reports contain only the chosen issue type, the general area you enter, the description, and a timestamp. The app does not ask for your name or phone number.
- Reports stay in `data/issue_reports.sqlite3` on this computer. They are not published, displayed to other visitors, or sent to a government office.
- Do not enter personal, sensitive, or emergency information. Use a general area instead of a home address.
- **AI can make mistakes.** Verify important facts with an official source. For an emergency in India, call **112** or visit [112 India](https://112.gov.in/); do not wait for an AI response.
- The report database is local demo storage, not a confidential case-management system. Anyone with access to this Windows account or project folder may be able to read its contents. Do not store sensitive reports here.

## Official links shown in the app

- [112 India — official emergency response](https://112.gov.in/)
- [Ministry of Health and Family Welfare](https://mohfw.gov.in/)
- [MyScheme — government schemes](https://www.myscheme.gov.in/)
- [National Scholarship Portal](https://scholarships.gov.in/)
- [National Government Services Portal](https://services.india.gov.in/)
- [CPGRAMS — public grievances](https://pgportal.gov.in/)

## Try this in your college demonstration

1. Start ManaSeva and show the English and Telugu language choices.
2. Select **Government schemes** and ask: “How can I check if I qualify for a government scheme?”
3. Show how the app points people to MyScheme instead of inventing eligibility rules.
4. Ask a health question and show the emergency warning and the 112 India link.
5. Enter a **made-up general area** and sample issue in the private report form. Explain that this demo stores it only on the local computer; it does not contact authorities.
6. If Ollama is available, show a local model answer. To show the offline demo, stop Ollama from its own application and refresh the page.

## Tests

With the virtual environment activated, run:

```powershell
python -m unittest discover -s tests -v
```

The tests cover offline English/Telugu answers, safety and official-resource guidance, private report storage, input validation, and an unavailable Ollama service.
