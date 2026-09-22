import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
from pathlib import Path
from PIL import Image
from io import BytesIO
from typing import Optional, Dict, List, Tuple


class BrandExtractor:
    def __init__(self, url: str, output_dir: str = "./brand_assets"):
        """
        Initialize the BrandExtractor with a URL.

        Args:
            url: The website URL to analyze
            output_dir: Directory to save downloaded assets
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.url = url
        self.output_dir = output_dir
        self.domain = urlparse(url).netloc.replace('www.', '')
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.page_html = None
        self.soup = None
        self.result = {
            'url': url,
            'domain': self.domain,
            'logo': None,
            'logo_url': None,
            'background_image': None,
            'background_image_url': None,
            'background_colors': [],
            'primary_font_color': None,
            'secondary_font_color': None,
            'button_color': None,
            'errors': []
        }

    def _fetch_page(self) -> bool:
        """Fetch the page using requests."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(self.url, timeout=10, headers=headers)
            response.raise_for_status()
            self.page_html = response.text
            self.soup = BeautifulSoup(self.page_html, 'html.parser')
            return True
        except Exception as e:
            self.result['errors'].append(f"Failed to fetch page: {str(e)}")
            return False

    def _hex_to_rgb(self, hex_color: str) -> Optional[Tuple[int, int, int]]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.strip().lstrip('#')
        try:
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            elif len(hex_color) == 3:
                return tuple(int(hex_color[i]*2, 16) for i in range(3))
        except ValueError:
            return None
        return None

    def _rgb_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color."""
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def _parse_color(self, color_str: str) -> Optional[str]:
        """Parse various color formats and return hex."""
        if not color_str:
            return None

        color_str = color_str.strip().lower()

        # Already hex
        if color_str.startswith('#'):
            rgb = self._hex_to_rgb(color_str)
            return color_str if rgb else None

        # RGB/RGBA format
        rgb_match = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_str)
        if rgb_match:
            r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
            return self._rgb_to_hex((r, g, b))

        # Named colors
        named_colors = {
            'white': '#ffffff', 'black': '#000000', 'red': '#ff0000',
            'green': '#008000', 'blue': '#0000ff', 'gray': '#808080',
            'grey': '#808080', 'transparent': None
        }

        return named_colors.get(color_str)

    def _find_logo(self) -> bool:
        """Find and download the logo."""
        logo_urls = []

        # Only use specific logo selectors - avoid pulling random images
        logo_selectors = [
            # Explicit logo matches
            ('img[src*="logo"]', 'src'),
            ('img[alt*="logo" i]', 'src'),  # Case insensitive alt text
            ('img.logo', 'src'),
            ('img#logo', 'src'),
            ('img[id*="logo"]', 'src'),
            ('a.logo img', 'src'),
            ('a#logo img', 'src'),
            # Logo in common containers
            ('[class*="logo"] img', 'src'),
            ('[id*="logo"] img', 'src'),
            # Brand/branding related
            ('img[class*="brand"]', 'src'),
            ('img.brand', 'src'),
            # SVG logos
            ('svg#logo', 'data'),
            ('svg.logo', 'data'),
            ('svg[id*="logo"]', 'data'),
            ('svg[class*="logo"]', 'data'),
        ]

        for selector, attr in logo_selectors:
            try:
                elements = self.soup.select(selector)
                for elem in elements:
                    url = None
                    if attr == 'data' and elem.name == 'svg':
                        svg_str = str(elem)
                        if svg_str and len(svg_str) > 50:  # Only if not empty
                            url = f"data:image/svg+xml,{svg_str}"
                    else:
                        url = elem.get(attr)

                    if url and url not in logo_urls:  # Avoid duplicates
                        logo_urls.append(urljoin(self.url, url))
                        if len(logo_urls) >= 3:  # Limit to 3 URLs to try
                            break
            except Exception:
                pass  # Silently fail on selector errors

        # Try first logo found
        if logo_urls:
            for logo_url in logo_urls:
                if self._download_logo(logo_url):
                    return True

            # If download failed for all URLs, return the first logo URL as fallback
            if logo_urls:
                self.result['logo_url'] = logo_urls[0]
                return True

        return False

    def _download_logo(self, logo_url: str) -> bool:
        """Download and save the logo."""
        try:
            # Handle inline SVG data
            if logo_url.startswith('data:image/svg+xml'):
                svg_str = logo_url.replace('data:image/svg+xml,', '')
                svg_bytes = svg_str.encode('utf-8')
                logo_path = os.path.join(self.output_dir, f"{self.domain}_logo.png")

                # Try to convert SVG to PNG, but don't fail if we can't
                try:
                    import cairosvg
                    cairosvg.svg2png(bytestring=svg_bytes, write_to=logo_path)
                    self.result['logo'] = logo_path
                    self.result['logo_url'] = "inline SVG"
                    return True
                except Exception:
                    # If SVG conversion fails, just return the URL
                    self.result['logo_url'] = logo_url
                    return False

            response = requests.get(logo_url, timeout=10)
            response.raise_for_status()

            # Check if response has content
            if not response.content:
                return False

            try:
                # Try to open as image (handles PNG, JPG, WebP, GIF, etc.)
                img = Image.open(BytesIO(response.content))

                # Convert to PNG
                if img.format and img.format != 'PNG':
                    img = img.convert('RGBA')
                elif not img.format:
                    # If format unknown, try to convert anyway
                    img = img.convert('RGBA')

                # Save logo
                logo_path = os.path.join(self.output_dir, f"{self.domain}_logo.png")
                img.save(logo_path, 'PNG')

                self.result['logo'] = logo_path
                self.result['logo_url'] = logo_url
                return True
            except Exception:
                # If image processing fails, still return the URL
                self.result['logo_url'] = logo_url
                return False

        except Exception as e:
            return False

    def _find_background_image(self) -> bool:
        """Find and download background image."""
        bg_image_urls = []

        # Check body and main sections for background images
        elements_to_check = [
            self.soup.find('body'),
            self.soup.find('main'),
            self.soup.find('header'),
            self.soup.find('section'),
            self.soup.find('[class*="hero"]'),
            self.soup.find('[class*="banner"]'),
        ]

        for elem in elements_to_check:
            if not elem:
                continue

            style = elem.get('style', '')
            # Look for background-image in style attribute
            bg_match = re.search(r'background(?:-image)?:\s*url\([\'"]?([^\)\'\"]+)[\'"]?\)', style)
            if bg_match:
                bg_url = bg_match.group(1)
                bg_image_urls.append(urljoin(self.url, bg_url))

        # Download first background image found
        if bg_image_urls:
            for bg_url in bg_image_urls:
                if self._download_background_image(bg_url):
                    return True

        return False

    def _download_background_image(self, bg_url: str) -> bool:
        """Download and save background image."""
        try:
            response = requests.get(bg_url, timeout=10)
            response.raise_for_status()

            # Try to open as image
            img = Image.open(BytesIO(response.content))

            # Save as PNG
            bg_path = os.path.join(self.output_dir, f"{self.domain}_background.png")
            if img.format != 'PNG':
                img = img.convert('RGB')
            img.save(bg_path, 'PNG')

            self.result['background_image'] = bg_path
            self.result['background_image_url'] = bg_url
            return True
        except Exception as e:
            self.result['errors'].append(f"Failed to download background image from {bg_url}: {str(e)}")
            return False

    def _extract_colors_from_css(self):
        """Extract colors from CSS stylesheets."""
        font_colors = set()
        button_colors = set()

        # Extract from style tags
        style_tags = self.soup.find_all('style')
        css_text = ''
        for style_tag in style_tags:
            css_text += style_tag.string or ''

        # Find color definitions in CSS
        color_matches = re.findall(r'color\s*:\s*([^;]+)', css_text)
        for match in color_matches[:10]:  # Get first 10 color definitions
            color = self._parse_color(match.strip())
            if color and color not in ['#ffffff', '#000000']:  # Skip pure white/black
                font_colors.add(color)

        # Find button background colors in CSS
        button_matches = re.findall(r'(?:button|\.btn|\.cta)\s*\{[^}]*background(?:-color)?:([^;]+)', css_text)
        for match in button_matches:
            color = self._parse_color(match.strip())
            if color:
                button_colors.add(color)

        return list(font_colors)[:2], list(button_colors)

    def _extract_colors(self):
        """Extract background, text, and button colors."""
        try:
            # Extract background color from body or main container
            body = self.soup.find('body')
            if body:
                body_style = body.get('style', '')
                bg_match = re.search(r'background(?:-color)?:\s*([^;]+)', body_style)
                if bg_match:
                    color = self._parse_color(bg_match.group(1))
                    if color:
                        self.result['background_colors'].append(color)

            # Extract from main container
            main = self.soup.find('main') or self.soup.find('div', class_=re.compile('container|main|content', re.I))
            if main:
                main_style = main.get('style', '')
                bg_match = re.search(r'background(?:-color)?:\s*([^;]+)', main_style)
                if bg_match:
                    color = self._parse_color(bg_match.group(1))
                    if color and color not in self.result['background_colors']:
                        self.result['background_colors'].append(color)

            # Find and extract button colors - improved detection
            button_selectors = [
                'button',
                'a.button',
                'a[role="button"]',
                '[class*="btn"]',
                '[class*="cta"]',
                'input[type="button"]',
                'input[type="submit"]',
            ]

            for selector in button_selectors:
                buttons = self.soup.select(selector)
                for button in buttons:
                    button_style = button.get('style', '')

                    # Button color
                    color_match = re.search(r'background(?:-color)?:\s*([^;]+)', button_style)
                    if color_match and not self.result['button_color']:
                        self.result['button_color'] = self._parse_color(color_match.group(1))

                    if self.result['button_color']:
                        break

                if self.result['button_color']:
                    break

            # Extract text colors - find primary and secondary from inline styles
            font_colors = []
            text_elements = self.soup.find_all(['p', 'a', 'h1', 'h2', 'h3', 'span', 'li'])

            for elem in text_elements[:20]:  # Sample first 20 text elements
                elem_style = elem.get('style', '')
                color_match = re.search(r'color:\s*([^;]+)', elem_style)
                if color_match:
                    color = self._parse_color(color_match.group(1))
                    if color and color not in font_colors:
                        font_colors.append(color)

            # Also extract from CSS stylesheets
            css_font_colors, css_button_colors = self._extract_colors_from_css()
            font_colors.extend(css_font_colors)

            # Set primary and secondary font colors
            if font_colors:
                self.result['primary_font_color'] = font_colors[0]
                if len(font_colors) > 1:
                    self.result['secondary_font_color'] = font_colors[1]

            # Set button color from CSS if not found in inline styles
            if not self.result['button_color'] and css_button_colors:
                self.result['button_color'] = css_button_colors[0]

        except Exception as e:
            self.result['errors'].append(f"Error extracting colors: {str(e)}")

    def extract(self) -> Dict:
        """
        Main method to extract all brand information.

        Returns:
            Dictionary containing extracted brand information
        """
        try:
            if not self._fetch_page():
                return self.result

            # Extract logo
            self._find_logo()

            # Extract background image
            self._find_background_image()

            # Extract colors from HTML/CSS
            self._extract_colors()

            # Clean up background colors if empty
            if not self.result['background_colors']:
                self.result['background_colors'] = ['#ffffff']  # Default to white

            return self.result

        except Exception as e:
            self.result['errors'].append(f"Unexpected error: {str(e)}")
            return self.result


def extract_brand(url: str, output_dir: str = "./brand_assets") -> Dict:
    """
    Convenience function to extract brand information from a URL.

    Args:
        url: Website URL to analyze
        output_dir: Directory to save logo assets

    Returns:
        Dictionary with extracted brand information
    """
    extractor = BrandExtractor(url, output_dir)
    return extractor.extract()


if __name__ == "__main__":
    import json

    # Example usage
    test_url = "https://www.github.com"
    result = extract_brand(test_url)

    print(json.dumps({k: v for k, v in result.items() if k != 'errors'}, indent=2))
    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"  - {error}")
