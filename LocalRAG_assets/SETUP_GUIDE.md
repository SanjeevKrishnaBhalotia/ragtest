# LocalRAG - Complete Setup Guide for Windows

## 📋 System Requirements

### Minimum Requirements
- **Operating System**: Windows 10 or 11 (64-bit)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 10GB free space (more for larger models)
- **CPU**: Any modern quad-core processor
- **Internet**: Required for initial setup and model downloads

### Recommended Specifications
- **RAM**: 16GB or more
- **Storage**: 50GB+ free space
- **CPU**: 8-core processor or better
- **SSD**: For faster model loading

## 🚀 Installation Process

### Step 1: Install Laragon (5 minutes)
1. **Download Laragon**:
   - Go to **https://laragon.org**
   - Click **"Download"** 
   - Choose **"Laragon Full"** (includes everything)
   - Save to Downloads folder

2. **Install Laragon**:
   - Run installer **as Administrator**
   - Accept default location: `C:\laragon`
   - Check all installation options
   - Wait for installation (2-3 minutes)

3. **Start Laragon**:
   - Look for Laragon icon in system tray
   - Right-click → **"Start All"**
   - Services should show green status

### Step 2: Add Python to Laragon (3 minutes)
1. **Add Python**:
   - Right-click Laragon icon → **"Quick add"** → **"Python"**
   - Select **"Python 3.11"** (recommended)
   - Wait for automatic download and installation

2. **Verify Installation**:
   - Right-click Laragon → **"Terminal"**
   - Type: `python --version`
   - Should show: `Python 3.11.x`

### Step 3: Install LocalRAG (2 minutes)
1. **Extract the ZIP**:
   - Extract `LocalRAG_Complete_System_Full.zip`
   - Note the location of the extracted folder

2. **Run Installation**:
   - Navigate to extracted folder
   - Right-click `install_localrag.bat`
   - Select **"Run as administrator"**
   - Follow the installation prompts

3. **Installation Process**:
   - Script copies files to `C:\laragon\www\LocalRAG`
   - Creates Python virtual environment
   - Installs all dependencies (3-5 minutes)
   - Creates desktop shortcut

### Step 4: First Launch (5 minutes)
1. **Launch LocalRAG**:
   - Double-click **LocalRAG** desktop shortcut
   - Wait for application to start (30-60 seconds first time)

2. **Create Master Password**:
   - Enter a strong password (8+ characters)
   - **⚠️ CRITICAL**: Write this password down securely!
   - This encrypts ALL your data - cannot be recovered if lost

3. **Download AI Model**:
   - Go to **"AI Models"** tab
   - Click **"Download Model"**
   - **Choose based on your RAM**:
     - 4-8GB RAM: Llama 3.2 1B (800MB)
     - 8-16GB RAM: Phi-3 Mini (2.2GB)
     - 16GB+ RAM: Llama 3.2 3B (1.9GB)
   - Wait for download (5-20 minutes)

### Step 5: Create Knowledge Base (3 minutes)
1. **Create Database**:
   - Go to **"Databases"** tab
   - Click **"Create New"**
   - Enter name: "My First Knowledge Base"
   - Add description (optional)
   - Click **"OK"**

2. **Import Documents**:
   - Select your new database
   - Click **"Import Documents"**
   - Choose PDF, DOCX, TXT, or CSV files
   - Select **chunking mode**:
     - **General**: Most documents
     - **Statute**: Legal documents
     - **Letter**: Structured reports
   - Click **"OK"** and wait for processing

### Step 6: Ask Your First Question (1 minute)
1. **Go to Query Assistant**:
   - Click **"Query Assistant"** tab
   - Select your AI model (dropdown)
   - Select your database (check the box)

2. **Ask a Question**:
   - Type a question about your documents
   - Click **"Ask Question"**
   - Watch the real-time feedback!
   - Review answer and sources

## 🔧 Advanced Features

### Multi-Database Querying
- Create multiple databases for different topics
- Select multiple databases for comprehensive searches
- Cross-database re-ranking for best results

### Prompt Workshop
- Use pre-built templates for different tasks
- Create custom prompt chains
- Execute multi-step analysis workflows

### Security Features
- All databases encrypted with AES-256
- Complete audit logging
- No data ever leaves your computer
- HIPAA-compliant for medical/legal use

## 🛠️ Troubleshooting

### Common Issues

**"Failed to load model"**:
- Check model file exists in `models/` folder
- Restart LocalRAG
- Try downloading model again

**"Database not found"**:
- Verify master password is correct
- Check `databases/` folder for encrypted files

**"Application won't start"**:
- Ensure Laragon is running (green status)
- Check Python is installed in Laragon
- Run from terminal to see error messages

**"Import failed"**:
- Verify file format is supported
- Check file size is under 100MB
- Try with smaller files first

### Performance Optimization

**For 4GB RAM**:
- Use Llama 3.2 1B model only
- Limit to 1-2 small databases
- Reduce chunk size to 500

**For 8GB RAM**:
- Use Phi-3 Mini or Llama 3.2 1B
- Can handle 3-5 databases
- Normal settings work well

**For 16GB+ RAM**:
- Use any model
- Multiple large databases
- Can increase chunk size to 1500

## 🔒 Security Best Practices

1. **Strong Master Password**: 12+ characters, mix of letters/numbers/symbols
2. **Secure Password Storage**: Write down and store securely
3. **Regular Backups**: Back up entire LocalRAG folder
4. **System Updates**: Keep Windows updated
5. **Access Control**: Don't share your LocalRAG folder

## 🎯 Success Metrics

You know it's working when:
- ✅ Models download and load successfully
- ✅ Documents import without errors
- ✅ Queries return relevant answers with sources
- ✅ Real-time feedback shows processing steps
- ✅ Multiple databases can be queried together
- ✅ Prompt chains execute successfully

## 📞 Getting Help

**Log Files**: Check `logs/` folder for detailed errors  
**Configuration**: Settings in `app/config/config.json`  
**Reset**: Delete `databases/` folder to start fresh (loses data!)

**Congratulations! You now have a complete, secure, local AI assistant!** 🎉
