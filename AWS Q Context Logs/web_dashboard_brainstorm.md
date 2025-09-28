# Web Dashboard Design - Distributed Transcript Generation System

## System Context

### Architecture Overview
- **Master/Worker Distributed System**: PostgreSQL-based orchestration across multiple machines
- **Node Types**: Generation nodes (GPU/CPU inference), Processing nodes (quality control), Master node (orchestration)
- **Hardware Mix**: Desktop workstations (EPM_DELL, MSI), Raspberry Pi 4/5 nodes, mixed GPU configurations
- **LLM Integration**: Local models (LM Studio, Ollama, llama.cpp), OpenAI API for grading
- **Output Format**: Amazon Lex Contact Lens v1.1.0 JSON for chatbot training

### Current System Components
- **Master Orchestrator**: Job creation, node discovery, health monitoring, failover management
- **Generation Nodes**: LLM inference, conversation generation, activity detection, thermal throttling
- **Quality Pipeline**: Deduplication (hash-based), OpenAI grading, healthcare validation, GAN-style feedback
- **Data Management**: RAG integration, public dataset processing, PII scrubbing, LEX export

### Key Metrics Tracked
- **Performance**: Tokens/second, conversations/hour, generation duration, model response times
- **Quality**: Realness scores (1-10), coherence, naturalness, healthcare validation (true/false)
- **System Health**: Node heartbeats, job status, duplicate rates, error counts
- **Resource Usage**: CPU/GPU utilization, memory usage, thermal data, activity modes

## Web Dashboard Feature Roadmap

### 1st Priority - Core Monitoring & System Health

#### **System Overview Panel**
- **Active Nodes Grid**: Real-time status of all nodes (online/offline/stale)
- **Job Queue Status**: Pending, running, completed, failed job counts
- **Generation Progress**: Total conversations generated, target completion percentage, ETA
- **System-Wide Metrics**: Overall generation rate (conversations/hour), quality score averages

#### **Node Health Monitoring** (per node)
- **Hardware Metrics**:
  - CPU/GPU temperatures with color-coded warnings (Green <70°C, Yellow 70-80°C, Red >80°C)
  - CPU/GPU utilization (5-minute rolling averages)
  - System RAM usage and GPU VRAM usage (percentages)
  - Free disk space (critical for model storage)
  - Network bandwidth between nodes
- **Activity Status**: Current mode (idle/gaming/work/throttling) with throttle factors
- **Performance Indicators**: Current tokens/second, jobs completed, last heartbeat

#### **Basic Controls**
- **Emergency Shutdown**: Stop all generation across cluster
- **Node Control**: Individual node start/stop/restart
- **Generation Pause/Resume**: Cluster-wide generation control

### 2nd Priority - Operational Control & Management

#### **Job Management Dashboard**
- **Active Job Monitoring**: Real-time view of running jobs with progress bars
- **Job Creation Interface**: Custom job parameters (scenario, conversation count, turn limits)
- **Queue Management**: Reorder, pause, cancel pending jobs
- **Batch Operations**: Bulk job creation, mass parameter updates

#### **Quality Control Center**
- **Grading Results**: Real-time quality scores, healthcare validation rates
- **Duplicate Detection**: Hash collision rates, semantic similarity statistics
- **Conversation Samples**: Preview generated conversations with quality scores
- **Rejection Analytics**: Why conversations are being rejected/deleted

#### **Configuration Management**
- **Generation Settings**: Temperature, max tokens, retry limits per node
- **Scenario Weights**: Adjust probability distribution for conversation types
- **Threshold Controls**: Quality minimums, duplicate sensitivity, thermal limits
- **Model Selection**: Switch between available LLM endpoints per node

#### **Data Export & Reports**
- **LEX Export**: Download Contact Lens formatted files with PII scrubbing options
- **Performance Reports**: CSV exports of generation metrics, quality trends
- **System Logs**: Filtered views of errors, warnings, node events
- **Conversation Archives**: Bulk download of generated conversations

#### **Alert System**
- **Real-Time Notifications**: Failed jobs, node disconnections, quality drops
- **Threshold Alerts**: Temperature warnings, performance degradation, disk space
- **Email/SMS Integration**: Critical system alerts for remote monitoring

### 3rd Priority - Advanced Intelligence & Analytics

#### **Performance Analytics Engine**
- **Rolling Charts** (interactive, zoomable):
  - **Tokens/Second Trends**: Per-node and per-model performance over time (30min real-time, 24hr trends, 7-day history)
  - **Generation Rate**: Conversations completed over time with trend analysis
  - **Quality Score Evolution**: Average grades trending up/down with model improvements
  - **Resource Correlation**: Overlay performance with temperature/memory/activity data

#### **Advanced Diagnostics**
- **Performance Cliff Detection**: Automatic alerts when tokens/sec drops >50% in 5 minutes
- **Thermal Correlation**: Visual correlation between temperature and performance degradation
- **Activity Impact Analysis**: How gaming/work modes affect generation efficiency
- **Model Comparison**: Side-by-side performance analysis of different LLMs on same hardware

#### **GAN Feedback Loop Visualization**
- **Discriminator Results**: Visual representation of conversation quality improvements
- **Prompt Evolution Tracking**: How prompts are automatically refined over time
- **Quality Trend Analysis**: Long-term improvement in conversation realism
- **Scenario Optimization**: Which conversation types are improving fastest

#### **Dataset Management Interface**
- **RAG Corpus Browser**: Explore and manage training examples from public datasets
- **Public Dataset Integration**: Import/process Kaggle, HuggingFace datasets
- **Conversation Search**: Semantic search through generated conversations
- **Data Quality Metrics**: Corpus diversity, coverage analysis

#### **Natural Language Query Interface**
- **Conversational Requests**: "Generate 500 frustrated healthcare calls with insurance issues"
- **Smart Parameter Inference**: Automatically set appropriate generation parameters
- **Query History**: Save and reuse common generation requests
- **Batch Query Processing**: Queue multiple natural language requests

#### **Model Marketplace & A/B Testing**
- **Model Performance Comparison**: Benchmark different LLMs across hardware
- **Endpoint Management**: Add/remove/test different model servers
- **A/B Testing Framework**: Compare model outputs for quality/speed
- **Cost Analysis**: Track API costs vs local inference efficiency

## Technical Architecture Requirements

### **Frontend Technology Stack**
- **Framework**: React or Vue.js for responsive, real-time interface
- **Charts**: Chart.js or D3.js for performance visualizations
- **Real-Time Updates**: WebSocket connections for live data streaming
- **Mobile Responsive**: Touch-friendly interface for remote monitoring
- **State Management**: Redux/Vuex for complex application state

### **Backend Integration**
- **API Layer**: RESTful endpoints integrated with master orchestrator
- **WebSocket Server**: Real-time data streaming to frontend clients
- **Database Integration**: Direct PostgreSQL queries for metrics and configuration
- **Authentication**: JWT-based auth with role-based access control
- **Caching**: Redis for frequently accessed metrics and real-time data

### **Data Collection Strategy**
- **Metrics Sampling**: 5-second hardware samples, 1-minute performance averages
- **Data Retention**: 24-hour detailed metrics, 30-day aggregated trends
- **Storage Optimization**: Time-series database for efficient metric storage
- **Real-Time Streaming**: Live metric updates via WebSocket connections

### **Security & Access Control**
- **Role-Based Access**: Admin (full control), Operator (monitoring + basic control), Viewer (read-only)
- **Secure Communications**: HTTPS/WSS for all web traffic
- **API Authentication**: Token-based access for programmatic control
- **Audit Logging**: Track all configuration changes and control actions

## Integration Points

### **Master Orchestrator Integration**
- **Health Monitoring**: Extend existing node health checks with hardware metrics
- **Job Management**: Web interface for job creation/management APIs
- **Configuration Updates**: Live configuration changes without system restart
- **Performance Tracking**: Enhanced metrics collection and storage

### **Node Agent Requirements**
- **Hardware Monitoring**: CPU/GPU temperature, utilization, memory reporting
- **Performance Metrics**: Tokens/second calculation and reporting
- **WebSocket Client**: Real-time metric streaming to dashboard
- **Remote Control**: Accept configuration updates and control commands

### **Database Schema Extensions**
- **Metrics Tables**: Time-series storage for performance and hardware data
- **Configuration Storage**: Centralized settings with version control
- **Alert History**: Log of all system alerts and notifications
- **User Sessions**: Dashboard user authentication and session management

This comprehensive dashboard would transform the distributed transcript generation system from a command-line operation into a sophisticated, visually-managed platform suitable for production deployment and scaling.