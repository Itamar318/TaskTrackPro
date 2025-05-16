from bs4 import BeautifulSoup
import re
import requests
from urllib.parse import urljoin
import logging
from io import BytesIO
from PIL import Image
import base64
import cssutils
import colorsys

# Suppress cssutils logging
cssutils.log.setLevel(logging.CRITICAL)

def extract_colors(soup, html_content, max_colors=5):
    """
    Extract dominant colors from a website
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        html_content (str): Raw HTML content
        max_colors (int): Maximum number of colors to extract
        
    Returns:
        list: List of hex color codes
    """
    colors = []
    
    # Extract colors from CSS
    try:
        # Find all style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                style_content = style_tag.string
                # Parse the CSS
                sheet = cssutils.parseString(style_content)
                # Extract colors from each rule
                for rule in sheet:
                    if hasattr(rule, 'style'):
                        for property_name in rule.style:
                            property_value = rule.style[property_name]
                            # Check if the property value contains a color
                            if 'color' in property_name or 'background' in property_name:
                                # Extract hex colors
                                hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}', property_value)
                                colors.extend(hex_colors)
                                # Extract rgb/rgba colors
                                rgb_colors = re.findall(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', property_value)
                                for r, g, b in rgb_colors:
                                    hex_color = '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))
                                    colors.append(hex_color)
        
        # Find inline styles
        elements_with_style = soup.find_all(style=True)
        for element in elements_with_style:
            style_content = element['style']
            # Extract hex colors
            hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}', style_content)
            colors.extend(hex_colors)
            # Extract rgb/rgba colors
            rgb_colors = re.findall(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', style_content)
            for r, g, b in rgb_colors:
                hex_color = '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))
                colors.append(hex_color)
                
        # Find linked stylesheets
        for link in soup.find_all('link', rel='stylesheet'):
            if 'href' in link.attrs:
                # Skip external CDN stylesheets
                if not any(cdn in link['href'] for cdn in ['googleapis', 'cdnjs', 'cloudflare']):
                    continue
    
    except Exception as e:
        logging.warning(f"Error extracting colors from CSS: {str(e)}")
    
    # Normalize colors (lowercase, remove duplicates)
    colors = [c.lower() for c in colors]
    unique_colors = list(set(colors))
    
    # Filter out black, white, transparent
    filtered_colors = [c for c in unique_colors if c not in ['#000', '#000000', '#fff', '#ffffff', 'transparent']]
    
    # If we have too few colors, look for commonly used CSS color names
    if len(filtered_colors) < 2:
        common_color_names = ['primary', 'secondary', 'accent', 'main', 'brand']
        for name in common_color_names:
            color_props = re.findall(fr'--{name}(?:-color)?\s*:\s*([^;]+)', html_content)
            for prop in color_props:
                hex_match = re.search(r'#(?:[0-9a-fA-F]{3}){1,2}', prop)
                if hex_match:
                    filtered_colors.append(hex_match.group(0).lower())
    
    # Sort colors by perceptual distinctiveness
    if len(filtered_colors) > 1:
        sorted_colors = sort_colors_by_distinctiveness(filtered_colors)
        return sorted_colors[:max_colors]
    
    return filtered_colors[:max_colors]

def sort_colors_by_distinctiveness(colors):
    """
    Sort colors by perceptual distinctiveness to get a good palette
    
    Args:
        colors (list): List of hex color codes
        
    Returns:
        list: Sorted list of hex color codes
    """
    # Convert hex to HSV for better perceptual sorting
    hsv_colors = []
    for color in colors:
        # Normalize the hex color
        if len(color) == 4:  # Convert #rgb to #rrggbb
            r = int(color[1] + color[1], 16) / 255.0
            g = int(color[2] + color[2], 16) / 255.0
            b = int(color[3] + color[3], 16) / 255.0
        else:
            r = int(color[1:3], 16) / 255.0
            g = int(color[3:5], 16) / 255.0
            b = int(color[5:7], 16) / 255.0
        
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        hsv_colors.append((color, h, s, v))
    
    # Sort by hue primarily
    hsv_colors.sort(key=lambda x: x[1])
    
    # Pick colors with good spacing
    result = []
    if hsv_colors:
        result.append(hsv_colors[0][0])
        
        # If we have more than one color, try to maximize distinctiveness
        if len(hsv_colors) > 1:
            # Sort remaining colors by saturation (more saturated colors are more distinctive)
            remaining = sorted(hsv_colors[1:], key=lambda x: x[2], reverse=True)
            for color_info in remaining:
                result.append(color_info[0])
    
    return result

def extract_logo(soup, base_url):
    """
    Extract the logo URL from a website
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        base_url (str): Base URL for resolving relative links
        
    Returns:
        str: URL of the logo image
    """
    # Common logo selectors
    logo_selectors = [
        {'tag': 'img', 'attrs': {'class': re.compile(r'logo', re.I)}},
        {'tag': 'img', 'attrs': {'id': re.compile(r'logo', re.I)}},
        {'tag': 'img', 'attrs': {'alt': re.compile(r'logo', re.I)}},
        {'tag': 'img', 'attrs': {'src': re.compile(r'logo', re.I)}},
        {'tag': 'a', 'attrs': {'class': re.compile(r'logo', re.I)}, 'find_child': 'img'},
        {'tag': 'div', 'attrs': {'class': re.compile(r'logo', re.I)}, 'find_child': 'img'},
        {'tag': 'svg', 'attrs': {'class': re.compile(r'logo', re.I)}},
    ]
    
    # Try each selector
    for selector in logo_selectors:
        elements = soup.find_all(selector['tag'], selector['attrs'])
        for element in elements:
            # If we need to find a child element
            if 'find_child' in selector:
                child = element.find(selector['find_child'])
                if child and 'src' in child.attrs:
                    logo_url = urljoin(base_url, child['src'])
                    return logo_url
            # If the element is an image
            elif element.name == 'img' and 'src' in element.attrs:
                logo_url = urljoin(base_url, element['src'])
                return logo_url
            # If the element is an SVG
            elif element.name == 'svg':
                # Return SVG as data URI
                svg_str = str(element)
                svg_base64 = base64.b64encode(svg_str.encode('utf-8')).decode('utf-8')
                return f"data:image/svg+xml;base64,{svg_base64}"
    
    # Check the header area specifically
    header = soup.find(['header', 'div'], {'class': re.compile(r'header', re.I)})
    if header:
        logo_img = header.find('img')
        if logo_img and 'src' in logo_img.attrs:
            logo_url = urljoin(base_url, logo_img['src'])
            return logo_url
    
    # Check for link to home with image inside
    home_links = soup.find_all('a', {'href': ['/']})
    for link in home_links:
        img = link.find('img')
        if img and 'src' in img.attrs:
            logo_url = urljoin(base_url, img['src'])
            return logo_url
    
    return None

def identify_fonts(soup, html_content):
    """
    Identify fonts used on a website
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        html_content (str): Raw HTML content
        
    Returns:
        list: List of font family names
    """
    fonts = []
    
    # Extract fonts from CSS
    try:
        # Look for Google Fonts
        google_fonts_links = soup.find_all('link', href=re.compile(r'fonts\.googleapis\.com'))
        for link in google_fonts_links:
            href = link.get('href', '')
            # Extract font names from Google Fonts URL
            if 'family=' in href:
                family_part = href.split('family=')[1].split('&')[0]
                font_families = family_part.split('|')
                for family in font_families:
                    # Remove weight/style specifications
                    clean_family = re.sub(r':[^,]+', '', family)
                    # Replace '+' with spaces
                    clean_family = clean_family.replace('+', ' ')
                    fonts.append(clean_family)
        
        # Check for @font-face rules
        font_face_matches = re.findall(r'@font-face\s*{[^}]+font-family\s*:\s*[\'"]([^\'"]+)[\'"]', html_content)
        fonts.extend(font_face_matches)
        
        # Check for font-family properties in style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                font_family_matches = re.findall(r'font-family\s*:\s*([^;}]+)', style_tag.string)
                for match in font_family_matches:
                    # Extract individual font families
                    for family in match.split(','):
                        family = family.strip()
                        # Remove quotes
                        family = re.sub(r'^[\'"]|[\'"]$', '', family)
                        if family and family.lower() not in ['sans-serif', 'serif', 'monospace']:
                            fonts.append(family)
        
        # Check inline styles
        elements_with_style = soup.find_all(style=True)
        for element in elements_with_style:
            style_content = element['style']
            if 'font-family' in style_content:
                font_family_matches = re.findall(r'font-family\s*:\s*([^;}]+)', style_content)
                for match in font_family_matches:
                    # Extract individual font families
                    for family in match.split(','):
                        family = family.strip()
                        # Remove quotes
                        family = re.sub(r'^[\'"]|[\'"]$', '', family)
                        if family and family.lower() not in ['sans-serif', 'serif', 'monospace']:
                            fonts.append(family)
                            
        # Check for CSS variables related to fonts
        font_vars = re.findall(r'--(?:font|typography)-family(?:-[a-z]+)?\s*:\s*([^;}]+)', html_content)
        for var in font_vars:
            # Extract individual font families
            for family in var.split(','):
                family = family.strip()
                # Remove quotes
                family = re.sub(r'^[\'"]|[\'"]$', '', family)
                if family and family.lower() not in ['sans-serif', 'serif', 'monospace']:
                    fonts.append(family)
                    
    except Exception as e:
        logging.warning(f"Error identifying fonts: {str(e)}")
    
    # Normalize and deduplicate
    normalized_fonts = []
    for font in fonts:
        font = font.strip()
        # Skip generic family names and empty strings
        if font and font.lower() not in ['sans-serif', 'serif', 'monospace', 'cursive', 'fantasy', '']:
            normalized_fonts.append(font)
    
    # Remove duplicates and sort
    unique_fonts = sorted(list(set(normalized_fonts)))
    
    return unique_fonts
