# Algorate Admin Systems

A comprehensive administrative platform for the Algorate horse racing analytics system. This production-ready Flask application provides centralized management for data imports, system monitoring, user administration, and operational oversight.

## 🏗️ System Architecture

### **Modular Design**
```
src/
├── modules/
│   ├── imports/          # Data import services
│   │   └── meetings/     # Meeting data imports
│   ├── admin/            # Administrative functions
│   │   ├── dashboard.py  # System dashboard
│   │   └── user.py       # User management
│   └── auth/             # Authentication system
├── shared/               # Shared models and utilities
└── static/               # Frontend dashboard
```

### **Core Modules**

#### 🔄 **Data Import System**
- **Meetings Import:** Automated and manual import from Punting Form API
- **Future Modules:** Races, results, selections, and analytics data
- **Comprehensive Logging:** Detailed import history and error tracking
- **Scheduling:** Automated daily imports with manual override capability

#### 📊 **Admin Dashboard**
- **Real-time Monitoring:** System status and import progress
- **Import Management:** Manual triggers with date selection
- **Historical Logs:** Searchable import history with filtering
- **System Health:** API connectivity and database status monitoring

#### 🔐 **Authentication & Security**
- **Admin Access Control:** Password-protected administrative functions
- **Session Management:** Secure login/logout functionality
- **Database Security:** Row Level Security (RLS) with Supabase
- **Environment-based Configuration:** Secure credential management

## 🚀 Features

### **Current Capabilities**
- ✅ **Meetings Data Import** with Punting Form API integration
- ✅ **Professional Admin Dashboard** with responsive design
- ✅ **Comprehensive Logging** and error tracking
- ✅ **Australian Date/Time Formatting** (DD/MM/YYYY, AEST)
- ✅ **Real-time Status Monitoring** with auto-refresh
- ✅ **Manual Import Controls** with date picker
- ✅ **API Connectivity Testing** and validation

### **Planned Expansions**
- 🔄 **Race Data Import** module
- 📈 **Results Processing** system
- 👥 **User Management** interface
- 📊 **Analytics Dashboard** with reporting
- 🔔 **Notification System** for alerts and updates
- ⚙️ **System Configuration** management

## 🛠️ Technology Stack

- **Backend:** Flask with modular blueprint architecture
- **Frontend:** Modern JavaScript with responsive UI design
- **Database:** Supabase PostgreSQL with RLS security
- **API Integration:** Punting Form API v2
- **Deployment:** Railway (Singapore region for geo-blocking avoidance)
- **Scheduling:** APScheduler for automated tasks
- **Authentication:** Session-based with password protection

## 📋 Environment Configuration

```bash
# Punting Form API
PUNTING_FORM_API_KEY=your_api_key_here

# Supabase Database
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Admin Authentication
ADMIN_PASSWORD=your_secure_admin_password

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
```

## 🔌 API Endpoints

### **Import Management**
- `POST /api/import/meetings` - Trigger manual meeting import
- `GET /api/import/meetings/status` - Get last import status
- `GET /api/import/meetings/logs` - Get import history
- `GET /api/import/meetings/test` - Test API connectivity

### **Admin Dashboard**
- `GET /api/dashboard/stats` - Get system statistics
- `GET /api/system/health` - Get system health status

### **Authentication**
- `POST /api/auth/login` - Admin login
- `POST /api/auth/logout` - Admin logout  
- `GET /api/auth/status` - Check authentication status

## 🚀 Deployment Guide

### **Local Development**

1. **Clone and Setup**
```bash
git clone <repository-url>
cd algorate-admin-systems
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Run Development Server**
```bash
python src/main.py
```

4. **Access Dashboard**
```
http://localhost:5000
```

### **Railway Production Deployment**

1. **Create Railway Project**
   - Connect GitHub repository
   - Select Singapore region (asia-southeast1)
   - Configure environment variables

2. **Database Setup**
   - Ensure Supabase tables exist with proper schema
   - Enable Row Level Security (RLS)
   - Configure service role permissions

3. **Deploy and Monitor**
   - Railway auto-deploys on git push
   - Monitor via Railway dashboard and admin interface

## 📊 Database Schema

### **Core Tables**
- **meetings:** Racing meeting data from Punting Form API
- **import_logs:** Comprehensive import tracking and statistics
- **users:** Admin user management (future expansion)

### **Security Model**
- **RLS Policies:** Database-level access control
- **Service Role:** Secure API access for imports
- **Session Management:** Admin authentication tracking

## 🔍 Monitoring & Maintenance

### **Admin Dashboard Features**
- Real-time import status monitoring
- Historical log analysis with filtering
- System health checks and API validation
- Manual import controls with date selection

### **Operational Monitoring**
- Railway deployment logs and metrics
- Supabase database performance monitoring
- Import success/failure rate tracking
- API connectivity and response time monitoring

## 🛡️ Security Features

- **Environment-based Configuration:** No hardcoded credentials
- **Database RLS:** Row-level security policies
- **Admin Authentication:** Password-protected access
- **CORS Configuration:** Secure cross-origin requests
- **Input Validation:** Comprehensive request validation

## 📈 Future Roadmap

### **Phase 2: Expanded Data Imports**
- Race data import module
- Results processing system
- Selection data integration

### **Phase 3: Advanced Administration**
- User management interface
- Role-based access control
- System configuration management

### **Phase 4: Analytics & Reporting**
- Performance analytics dashboard
- Custom reporting system
- Data visualization components

---

**Algorate Admin Systems** - Comprehensive administrative platform for advanced horse racing analytics and data management.

