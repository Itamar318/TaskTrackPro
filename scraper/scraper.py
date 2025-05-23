import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin, urlparse
from .design_elements import extract_colors, extract_logo, identify_fonts
from .utils import is_valid_email, is_valid_phone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_website(url, profile, extract_colors=True, extract_logo=True, extract_fonts=True):
    """
    Main scraping function that extracts data based on the selected profile
    
    Args:
        url (str): Website URL to scrape
        profile (dict): Selected profile configuration
        extract_colors (bool): Whether to extract color palette
        extract_logo (bool): Whether to extract logo
        extract_fonts (bool): Whether to identify fonts
        
    Returns:
        tuple: (extracted_data, design_elements)
    """
    logger.info(f"Starting scraping for URL: {url}")
    
    try:
        # Make request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract data based on profile
        extracted_data = {}
        for field in profile["fields"]:
            value = extract_field(soup, field, url)
            extracted_data[field] = value
            
        # Extract design elements
        design_elements = {}
        
        if extract_colors:
            design_elements['colors'] = extract_color_palette(soup, response.text)
            
        if extract_logo:
            design_elements['logo_url'] = extract_logo(soup, url)
            
        if extract_fonts:
            design_elements['fonts'] = identify_fonts(soup, response.text)
        
        return extracted_data, design_elements
        
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to fetch website: {str(e)}")
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}")
        raise Exception(f"Error during scraping: {str(e)}")

def extract_field(soup, field_name, base_url):
    """
    Extract a specific field from the webpage
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        field_name (str): Name of the field to extract
        base_url (str): Base URL for resolving relative links
        
    Returns:
        str or list: Extracted data
    """
    # Business name extraction
    if field_name == "שם העסק":
        # Check title tag
        title = soup.title.text.strip() if soup.title else ""
        
        # Check for h1 tags
        h1_tags = soup.find_all('h1')
        if h1_tags:
            for h1 in h1_tags:
                if len(h1.text.strip()) > 3 and len(h1.text.strip()) < 50:
                    return h1.text.strip()
        
        # Check for logo alt text
        logo = soup.find('img', {'class': re.compile(r'logo|brand', re.I)})
        if logo and logo.get('alt'):
            return logo.get('alt')
            
        # Return title as fallback
        return title
    
    # Phone number extraction
    elif field_name == "טלפון":
        # Common patterns for phone numbers
        phone_patterns = [
            r'(?:\+972[- ]?|0)[2-9]{1}[- ]?\d{7}',  # Israeli format
            r'\+\d{1,3}[- ]?\d{1,4}[- ]?\d{4,}',    # International format
            r'\(\d{3,4}\)\s*\d{3}[- ]?\d{4}',       # (XXX) XXX-XXXX format
            r'\d{3}[- ]?\d{3}[- ]?\d{4}'            # XXX-XXX-XXXX format
        ]
        
        # Look for phone pattern in text
        text = soup.get_text()
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Filter out invalid matches
                valid_phones = [p for p in matches if is_valid_phone(p)]
                if valid_phones:
                    return valid_phones[0]
                    
        # Look for elements with tel: links
        tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
        if tel_links:
            for link in tel_links:
                phone = link['href'].replace('tel:', '')
                if is_valid_phone(phone):
                    return phone
                    
        return ""
    
    # Email extraction
    elif field_name == "דוא\"ל" or field_name == "דוא'ל" or field_name == "דוא״ל":
        # Look for mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
        if mailto_links:
            for link in mailto_links:
                email = link['href'].replace('mailto:', '').split('?')[0]
                if is_valid_email(email):
                    return email
        
        # Look for email patterns in text
        text = soup.get_text()
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.[a-z]{2,}', text)
        
        valid_emails = [e for e in emails if is_valid_email(e)]
        if valid_emails:
            return valid_emails[0]
            
        return ""
    
    # Address extraction
    elif field_name == "כתובת":
        # Look for address in meta tags
        meta_address = soup.find('meta', {'property': re.compile(r'og:address|place:location:address')})
        if meta_address and meta_address.get('content'):
            return meta_address.get('content')
        
        # Look for address in schema.org markup
        address_elem = soup.find('span', {'itemprop': 'address'})
        if address_elem:
            return address_elem.text.strip()
            
        # Look for common address patterns in Israel (city names followed by street)
        cities = ["תל אביב", "ירושלים", "חיפה", "באר שבע", "רמת גן", "הרצליה", "נתניה", "פתח תקווה", "אשדוד", "אילת"]
        
        for elem in soup.find_all(['p', 'div', 'span', 'address']):
            text = elem.text.strip()
            # Check if text contains a city name and looks like an address
            if any(city in text for city in cities) and len(text) < 100 and len(text) > 10:
                return text
        
        # Look for elements with address in class or id
        address_elems = soup.find_all(class_=re.compile(r'address|location', re.I))
        address_elems += soup.find_all(id=re.compile(r'address|location', re.I))
        
        if address_elems:
            for elem in address_elems:
                if len(elem.text.strip()) > 5 and len(elem.text.strip()) < 150:
                    return elem.text.strip()
                    
        return ""
    
    # Opening hours extraction
    elif field_name == "שעות פעילות" or field_name == "שעות פתיחה" or field_name == "שעות קבלה":
        # Look for common patterns for hours
        hours_elems = soup.find_all(class_=re.compile(r'hours|time|schedule', re.I))
        hours_elems += soup.find_all(id=re.compile(r'hours|time|schedule', re.I))
        
        # Common day names in Hebrew
        days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
        
        # Check elements with hours-related classes/ids
        for elem in hours_elems:
            text = elem.text.strip()
            # Check if the text contains day names and time patterns
            if any(day in text for day in days) and re.search(r'\d{1,2}[:.]\d{2}', text):
                # Clean up and format the hours
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                return "\n".join(lines)
                
        # Look for table with days and hours
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if 3 <= len(rows) <= 8:  # Typical number of rows for hours table
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells and any(day in cells[0].text for day in days):
                        hours = []
                        for row in rows:
                            row_text = " ".join([cell.text.strip() for cell in row.find_all(['td', 'th'])])
                            if row_text:
                                hours.append(row_text)
                        return "\n".join(hours)
                        
        return ""
    
    # Team/Staff extraction
    elif field_name == "צוות" or field_name == "רופאים":
        team = []
        # Look for team sections
        team_sections = soup.find_all(class_=re.compile(r'team|staff|personnel|people|about', re.I))
        team_sections += soup.find_all(id=re.compile(r'team|staff|personnel|people|about', re.I))
        
        for section in team_sections:
            # Look for person cards or list items
            person_elems = section.find_all(class_=re.compile(r'card|member|person|profile', re.I))
            
            if not person_elems:
                # Try finding them in list items
                person_elems = section.find_all('li')
            
            for person in person_elems:
                name = ""
                role = ""
                email = ""
                
                # Try to extract name
                name_elem = person.find(['h3', 'h4', 'h5', 'strong', 'b'])
                if name_elem:
                    name = name_elem.text.strip()
                
                # Try to extract role
                role_elem = person.find(class_=re.compile(r'role|position|title', re.I))
                if role_elem:
                    role = role_elem.text.strip()
                else:
                    # Look for paragraph or span that might contain the role
                    role_elem = person.find(['p', 'span'])
                    if role_elem and role_elem != name_elem:
                        role = role_elem.text.strip()
                
                # Try to extract email
                email_elem = person.find('a', href=re.compile(r'^mailto:'))
                if email_elem:
                    email = email_elem['href'].replace('mailto:', '')
                
                if name:  # Only add if we have at least a name
                    person_info = {"שם": name}
                    if role:
                        person_info["תפקיד"] = role
                    if email:
                        person_info["דוא\"ל"] = email
                    team.append(person_info)
            
            # If we found team members, return them
            if team:
                return team
        
        return []
    
    # Social media links extraction
    elif field_name == "קישורים לרשתות":
        social_links = {}
        social_patterns = {
            'facebook': r'facebook\.com',
            'twitter': r'twitter\.com|x\.com',
            'instagram': r'instagram\.com',
            'linkedin': r'linkedin\.com',
            'youtube': r'youtube\.com',
            'tiktok': r'tiktok\.com',
            'whatsapp': r'wa\.me|whatsapp\.com'
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            
            # Check if the link is a social media link
            for platform, pattern in social_patterns.items():
                if re.search(pattern, href):
                    # Resolve relative URLs
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(base_url, href)
                    
                    social_links[platform] = href
                    break
        
        return social_links
    
    # Business domain/field extraction
    elif field_name == "תחומי עיסוק" or field_name == "תחום פעילות" or field_name == "תחום התמחות":
        # Check meta tags
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = [k.strip() for k in meta_keywords.get('content').split(',')]
            if keywords:
                return keywords
        
        # Check for lists of services/specialties
        service_headers = soup.find_all(['h2', 'h3'], string=re.compile(r'שירותים|תחומי|התמחויות|פעילות', re.I))
        
        for header in service_headers:
            # Find the next list or div with potential services
            next_elem = header.find_next(['ul', 'div', 'section'])
            if next_elem:
                # If it's a list, get the list items
                if next_elem.name == 'ul':
                    services = [li.text.strip() for li in next_elem.find_all('li')]
                    if services:
                        return services
                # If it's a div, look for paragraphs or headers inside
                elif next_elem.name in ['div', 'section']:
                    services = []
                    for item in next_elem.find_all(['p', 'h4', 'h5', 'span']):
                        text = item.text.strip()
                        if 5 < len(text) < 100:  # Reasonable length for a service description
                            services.append(text)
                    if services:
                        return services
        
        # As a fallback, check for meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content')
            
        return ""
    
    # Default fallback: return empty result
    return ""
