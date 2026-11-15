# 🌍 Earth System Trend Detective

### Discover What Is Changing on Our Planet — Through NASA Data

**Earth System Trend Detective** is an interactive environmental data analysis application developed for the **NASA Space Apps Challenge 2026**. It helps users investigate long-term environmental changes using NASA POWER data, statistical trend detection methods, and interactive visualizations.

The project makes environmental data easier to explore by turning complex time-series analysis into understandable insights.

---

## 🚀 Project Overview

Environmental conditions are constantly changing. However, identifying meaningful long-term trends requires more than simply looking at a graph.

Earth System Trend Detective provides tools to investigate environmental variables, analyze historical patterns, compare locations, and assess whether observed trends are statistically significant.

Users can explore data, detect trends, examine the rate of change, and understand statistical results through an interactive interface.

## ✨ Key Features

### 1. 🔎 Environmental Trend Detective
- Investigate environmental variables for a selected geographical location.
- Explore historical monthly data.
- Visualize environmental changes over time.
- Identify increasing, decreasing, or statistically insignificant trends.
- Examine statistical results and trend estimates.

### 2. 📊 Statistical Trend Analysis
The application uses established statistical methods to investigate environmental time series:

- **Seasonal Mann-Kendall Test:** Detects monotonic trends while accounting for seasonal patterns.
- **Hamed-Rao Modified Mann-Kendall:** Helps account for autocorrelation in time-series data.
- **Theil-Sen Slope Estimator:** Estimates the magnitude and direction of a trend.
- **Pettitt Change-Point Test:** Investigates potential changes in the statistical behavior of a time series.
- **Benjamini-Hochberg FDR Correction:** Helps control false discoveries when multiple trends are tested.
- **Sensitivity Analysis:** Examines how results may change when different starting periods are selected.

### 3. 🌐 Trend Scanner
- Investigate trends across multiple geographical points.
- Explore regional environmental patterns.
- Identify locations with potentially significant trends.
- Compare trend direction and magnitude across a region.

### 4. 🗺️ Regional Map
- Explore geographical patterns through interactive maps.
- View environmental trend information across locations.
- Investigate how environmental changes vary spatially.

### 5. 🤖 AI-Assisted Explanations
The application includes optional AI-powered features using the Groq API.

AI features can:
- Explain statistical findings in beginner-friendly language.
- Help users understand environmental variables.
- Suggest potentially relevant variables based on a user's question.

**Scientific calculations are performed by the Python statistical analysis engine. AI is used to assist with explanations and suggestions, not to determine statistical significance.**

---

## 🛰️ NASA Data Source

The application retrieves environmental data from:

**NASA POWER — Prediction Of Worldwide Energy Resources**

NASA POWER provides access to environmental and meteorological data derived from satellite observations and model-based products.

The project uses the NASA POWER Monthly Point API to retrieve monthly data for geographical locations.

**NASA POWER Website:**  
https://power.larc.nasa.gov/

**NASA POWER API Documentation:**  
https://power.larc.nasa.gov/docs/

The exact variables and available historical periods depend on the selected NASA POWER parameters and data availability.

---

## ⚙️ How It Works

The application follows a data-to-insight workflow:

1. **Location Selection:** The user selects a geographical location and environmental variable.
2. **Data Retrieval:** The application requests monthly data from the NASA POWER API.
3. **Data Processing:** Python and Pandas organize and process the retrieved observations.
4. **Anomaly Analysis:** The application processes seasonal patterns to help investigate changes over time.
5. **Statistical Testing:** Trend detection methods evaluate the direction and statistical evidence of potential trends.
6. **Visualization:** Interactive charts and maps present the analysis results.
7. **Explanation:** Optional AI features help communicate the findings in accessible language.

---

## 🧪 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application and analysis |
| Streamlit | Interactive web interface |
| Pandas | Data processing and manipulation |
| NumPy | Numerical operations |
| SciPy | Scientific and statistical functions |
| PyMannKendall | Mann-Kendall trend analysis |
| Plotly | Interactive visualizations |
| Folium | Interactive geographical maps |
| Streamlit-Folium | Folium integration with Streamlit |
| Requests | NASA POWER API communication |
| Groq API | Optional AI-assisted explanations |

---

## 📁 Project Structure

```text
earthtrenddetector/
│
├── app.py              # Main Streamlit application
├── stats_engine.py     # Statistical trend analysis engine
├── scanner.py          # Regional trend scanning
├── data_fetcher.py     # NASA POWER data retrieval
├── ai_helper.py        # Optional AI assistance
├── config.py           # Application configuration
├── plain.py            # Plain-language support
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

---

## 💻 Installation and Setup

Follow these steps to run the project locally.

### Prerequisites

- Python 3.10 or newer
- Git
- Internet connection for NASA POWER data retrieval

### Step 1: Clone the Repository

```bash
git clone https://github.com/astrophileaqsa123/earthtrenddetector.git
```

### Step 2: Navigate to the Project Directory

```bash
cd earthtrenddetector
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

**Windows:**
```bash
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run the Application

```bash
streamlit run app.py
```

The application should open in your browser. If it does not, visit:

```text
http://localhost:8501
```

---

## 🔑 Optional AI Configuration

AI-powered explanations and suggestions use the Groq API.

The application can run without a Groq API key using its built-in fallback functionality.

To enable AI features, obtain an API key from:

https://console.groq.com/

For local development, create a `.streamlit/secrets.toml` file:

```toml
GROQ_API_KEY = "your_actual_groq_api_key"
```

Replace the placeholder with your actual API key.

**Security note:** Never commit API keys, passwords, or other secrets to a public GitHub repository.

For Streamlit Community Cloud, configure the key through the application's Secrets settings instead of committing it to GitHub.

---

## 📈 Scientific Methodology

Environmental time-series data can contain seasonal variations, autocorrelation, and random fluctuations. These characteristics can make trend detection challenging.

Earth System Trend Detective uses multiple statistical approaches to provide a more informative investigation.

### Seasonal Analysis
Seasonal patterns are considered during the analysis so that recurring variations do not automatically appear as long-term changes.

### Trend Detection
The Seasonal Mann-Kendall test is used to investigate whether a time series shows a statistically meaningful monotonic trend.

### Trend Magnitude
The Theil-Sen estimator provides an estimate of how quickly a variable is changing over time.

### Change-Point Investigation
The Pettitt test helps investigate whether a potential change point exists in the time series.

### Multiple-Testing Correction
The Benjamini-Hochberg procedure helps reduce false discoveries when many locations or variables are investigated.

### Robustness and Sensitivity
The application includes analysis features that help investigate whether findings remain consistent under different analysis choices.

---

## ⚠️ Limitations and Responsible Interpretation

- Statistical significance does not prove causation.
- A detected trend does not necessarily explain why an environmental variable is changing.
- NASA POWER data are based on gridded datasets and model-based products; they are not necessarily direct measurements from a weather station at the selected coordinates.
- Spatial resolution and accuracy depend on the selected data product.
- Results depend on the selected variable, geographical location, historical period, and data availability.
- Missing observations and data quality can affect statistical analysis.
- AI-generated explanations are intended to improve accessibility and should not replace scientific verification.

Users should interpret the results as evidence of statistical patterns, not definitive proof of environmental causes.

---

## 🌱 Project Impact

Earth System Trend Detective aims to make environmental data analysis more accessible to:

- Students learning about Earth science and climate.
- Educators teaching environmental data analysis.
- Researchers exploring long-term environmental patterns.
- Data enthusiasts interested in NASA datasets.
- People who want to understand changes in Earth's environmental systems.

By combining NASA data, statistical methods, and interactive visualizations, the project encourages evidence-based exploration of our changing planet.

---

## 🔮 Future Improvements

Potential future development includes:

- Integration of additional NASA and other trusted environmental datasets.
- Expanded geographical and temporal coverage.
- More environmental variables and analysis options.
- Improved regional comparison tools.
- Additional visualization and mapping capabilities.
- More educational explanations of statistical methods.
- Enhanced data validation and uncertainty communication.

---

## 🏆 NASA Space Apps Challenge 2026

**Challenge:** Be An Earth System Trend Detective!

Earth System Trend Detective was developed as a project for the NASA Space Apps Challenge 2026.

The project demonstrates how publicly available NASA environmental data can be combined with statistical analysis and interactive technology to help people investigate changes in Earth's systems.

---

## 🔗 Project Links

- **GitHub Repository:** https://github.com/astrophileaqsa123/earthtrenddetector
- **Live Application:** https://earthtrenddetector-lexyhltfm6hqqcuureffig.streamlit.app/
- 

---

## 🤝 Acknowledgements

We acknowledge NASA's POWER project for providing access to environmental data and the open-source Python community for the tools and libraries that make this application possible.

**Built with curiosity, data, and a passion for understanding our changing planet.**

### 🌍 Earth System Trend Detective
**Explore the Data. Detect the Trends. Understand Our Planet.**
