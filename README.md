# 📄 PaperGen AI — Advanced Question Paper Generator

PaperGen AI is a professional, AI-powered academic tool designed to automate the creation of high-quality question papers. It features a robust multi-set generation engine, an integrated approval workflow, and a modern, high-performance UI tailored for educational institutions.

## 🚀 Key Features

- **Multi-Set AI Generation**: Generate up to 5 unique sets of question papers (Set A, B, C...) from blueprints or uploaded PDFs/CSVs.
- **Academic Approval Workflow**: Faculty submit drafts; Admins review, comment, and approve/request changes.
- **Smart Notification System**: Live sidebar alerts and a dedicated notification center for real-time status updates.
- **Comprehensive Audit Logs**: Full transparency with searchable activity logs for logins, submissions, and security events.
- **Professional Exports**: Instant download of verified papers in **PDF**, **DOCX**, and **TXT** formats.
- **Premium UI/UX**: A sleek, responsive dashboard built with Streamlit and modern design principles.

## 🛠️ Tech Stack

- **Core Framework**: [Streamlit](https://streamlit.io/)
- **AI Engine**: [Google Gemini Pro](https://deepmind.google/technologies/gemini/) (via `google-genai`)
- **Database**: SQLite3 (Embedded)
- **Document Handlers**: FPDF (PDF), python-docx (DOCX), PyMuPDF (PDF Processing)
- **Styling**: Vanilla CSS & HSL design tokens

## 📦 Installation & Setup

### 1. Prerequisites
- Python 3.9+
- A Google Gemini API Key

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd ai-question-paper-generator

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory and add your API key:
```env
GEMINI_API_KEY=your_api_key_here
```

### 4. Running the Application

To launch the dashboard, use the following command from the root directory:

```bash
# Start the local Streamlit server
streamlit run app.py
```

After running, the application will typically be accessible at:
- **Local URL**: `http://localhost:8501`
- **Network URL**: `http://192.168.x.x:8501`

## 🛡️ Default Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@gmail.com` | `admin123` |

> [!NOTE]
> Faculty accounts must be created by the Administrator through the **Faculty Management** dashboard.

## 📂 Project Structure

- `app.py`: Main entry point.
- `dashboard/`: Admin and Faculty dashboard UI components.
- `modules/`: Core logic for AI generation, database, and exports.
- `login/`: Role-based authentication screens.
- `data/`: SQLite database storage.

---
© 2026 PaperGen AI. All rights reserved.
