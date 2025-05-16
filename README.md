# AD.IT.ASAP Web Scraper

A modular web scraping system that extracts both content and design elements (colors, fonts, logos) with configurable profiles for different business types.

## Features

- **Modular Design**: Each component (scraper, interface, settings, output) is written as an independent unit that can be extended or upgraded.
- **Open Configuration**: Separation of logic (code) from settings (JSON), dynamic definition of fields and profiles.
- **User-friendly Interface**: Streamlit-based UI with intuitive controls.
- **Flexible Profiles**: Predefined profiles for different business types (law firms, doctors, general businesses).
- **Design Element Extraction**: Extract color palettes, fonts, and logos from websites.
- **Data Export**: Export scraped data to CSV or JSON formats.
- **Extensible**: Easy to add new fields or features in the future.

## Getting Started

### Prerequisites

- Python 3.10+
- Dependencies: streamlit, beautifulsoup4, requests, cssutils, etc.

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   