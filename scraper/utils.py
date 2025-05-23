import json
import os
import re
from urllib.parse import urlparse

def load_profiles():
    """
    Load profile configurations from JSON file
    
    Returns:
        dict: Profile configurations
    """
    try:
        with open('config/profiles.json', 'r', encoding='utf-8-sig') as file:
            profiles = json.load(file)
        return profiles
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If file doesn't exist or has invalid JSON, return default profiles
        return {
            "law_firm": {
                "profile_name": "משרד עו\"ד",
                "fields": ["שם העסק", "כתובת", "טלפון", "דוא\"ל", "לוגו", "צבעים דומיננטיים", "תחומי עיסוק", "צוות", "קישורים לרשתות", "שעות פעילות"],
                "mandatory_fields": ["שם העסק", "כתובת", "טלפון"]
            },
            "doctor": {
                "profile_name": "מרפאה/רופא",
                "fields": ["שם העסק", "תחום התמחות", "כתובת", "טלפון", "דוא\"ל", "רופאים", "שעות קבלה", "קישורים לרשתות"],
                "mandatory_fields": ["שם העסק", "טלפון"]
            },
            "business": {
                "profile_name": "עסק כללי",
                "fields": ["שם העסק", "תחום פעילות", "כתובת", "טלפון", "דוא\"ל", "לוגו", "שעות פתיחה", "קישורים לרשתות"],
                "mandatory_fields": ["שם העסק"]
            },
            "custom": {
                "profile_name": "מותאם אישית",
                "fields": [],
                "mandatory_fields": []
            }
        }

def load_fields():
    """
    Load field configurations from JSON file
    
    Returns:
        list: Field configurations
    """
    try:
        with open('config/fields.json', 'r', encoding='utf-8') as file:
            fields = json.load(file)
        return fields
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If file doesn't exist or has invalid JSON, return default fields
        return [
            {"field": "שם העסק", "type": "string", "example": "עו\"ד חיים כהן ושות'", "regex": None, "profiles": ["law_firm", "doctor", "business"]},
            {"field": "טלפון", "type": "string", "example": "+972-3-5555555", "regex": "(?:\\+972[- ]?|0)[2-9]{1}-?\\d{7}", "profiles": ["law_firm", "doctor", "business"]},
            {"field": "דוא\"ל", "type": "email", "example": "office@lawfirm.co.il", "regex": "[\\w\\.-]+@[\\w\\.-]+\\.[a-z]{2,}", "profiles": ["law_firm", "doctor", "business"]},
            {"field": "לוגו", "type": "url", "example": "https://site.com/logo.png", "regex": None, "profiles": ["law_firm", "business"]},
            {"field": "צוות", "type": "array", "example": [{"שם": "עו\"ד רונית לוי", "תפקיד": "שותפה", "דוא\"ל": "ronit@lawfirm.co.il"}], "regex": None, "profiles": ["law_firm"]},
            {"field": "כתובת", "type": "string", "example": "רחוב הרצל 15, תל אביב", "regex": None, "profiles": ["law_firm", "doctor", "business"]},
            {"field": "שעות פעילות", "type": "string", "example": "א'-ה' 9:00-18:00, ו' 9:00-13:00", "regex": None, "profiles": ["law_firm", "business"]},
            {"field": "שעות קבלה", "type": "string", "example": "א'-ה' 9:00-18:00, ו' 9:00-13:00", "regex": None, "profiles": ["doctor"]},
            {"field": "שעות פתיחה", "type": "string", "example": "א'-ה' 9:00-18:00, ו' 9:00-13:00", "regex": None, "profiles": ["business"]},
            {"field": "תחומי עיסוק", "type": "array", "example": ["דיני משפחה", "דיני עבודה", "נזיקין"], "regex": None, "profiles": ["law_firm"]},
            {"field": "תחום התמחות", "type": "string", "example": "רפואת משפחה", "regex": None, "profiles": ["doctor"]},
            {"field": "תחום פעילות", "type": "string", "example": "מסעדה איטלקית", "regex": None, "profiles": ["business"]},
            {"field": "קישורים לרשתות", "type": "object", "example": {"facebook": "https://facebook.com/business", "instagram": "https://instagram.com/business"}, "regex": None, "profiles": ["law_firm", "doctor", "business"]},
            {"field": "רופאים", "type": "array", "example": [{"שם": "ד\"ר יעל לוי", "התמחות": "רפואת משפחה", "דוא\"ל": "yael@clinic.co.il"}], "regex": None, "profiles": ["doctor"]},
            {"field": "צבעים דומיננטיים", "type": "array", "example": ["#123456", "#789abc"], "regex": None, "profiles": ["law_firm", "business"]}
        ]

def validate_url(url):
    """
    Validate URL format
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: Whether URL is valid
    """
    if not url:
        return False
        
    if not url.startswith(('http://', 'https://')):
        return False
        
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_valid_email(email):
    """
    Validate email format
    
    Args:
        email (str): Email to validate
        
    Returns:
        bool: Whether email is valid
    """
    if not email:
        return False
        
    # Simple regex for email validation
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone):
    """
    Validate phone number format
    
    Args:
        phone (str): Phone number to validate
        
    Returns:
        bool: Whether phone number is valid
    """
    if not phone:
        return False
        
    # Remove common separators and spaces
    clean_phone = re.sub(r'[\s\-\(\)\.]+', '', phone)
    
    # Check if it's mostly digits
    if not re.match(r'^\+?[\d]{7,15}$', clean_phone):
        return False
        
    return True

def ensure_dirs():
    """
    Ensure required directories exist
    """
    dirs = ['config', 'scraper']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
