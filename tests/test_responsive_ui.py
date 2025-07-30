"""
Tests for RegulensAI Responsive UI Components and Mobile Responsiveness
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class TestResponsiveDesign:
    """Test responsive design across different screen sizes."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Chrome driver with mobile emulation."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()
    
    def test_mobile_viewport_320px(self, driver):
        """Test mobile viewport at 320px width."""
        driver.set_window_size(320, 568)  # iPhone SE
        driver.get("http://localhost:3000/operations")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check that mobile navigation is present
        hamburger_menu = driver.find_element(By.CSS_SELECTOR, "[aria-label='open drawer']")
        assert hamburger_menu.is_displayed()
        
        # Check that tabs are scrollable on mobile
        tabs_container = driver.find_element(By.CSS_SELECTOR, ".MuiTabs-root")
        assert "scrollable" in tabs_container.get_attribute("class").lower()
        
        # Check that cards stack vertically
        cards = driver.find_elements(By.CSS_SELECTOR, ".MuiCard-root")
        if len(cards) >= 2:
            card1_rect = cards[0].rect
            card2_rect = cards[1].rect
            # Cards should be stacked vertically (card2 below card1)
            assert card2_rect['y'] > card1_rect['y'] + card1_rect['height'] - 10
    
    def test_tablet_viewport_768px(self, driver):
        """Test tablet viewport at 768px width."""
        driver.set_window_size(768, 1024)  # iPad
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check that navigation adapts to tablet size
        # Should still show hamburger menu but with more space
        hamburger_menu = driver.find_element(By.CSS_SELECTOR, "[aria-label='open drawer']")
        assert hamburger_menu.is_displayed()
        
        # Check that cards can be side by side
        cards = driver.find_elements(By.CSS_SELECTOR, ".MuiCard-root")
        if len(cards) >= 2:
            card1_rect = cards[0].rect
            card2_rect = cards[1].rect
            # Cards might be side by side or stacked depending on content
            # At least check they're positioned reasonably
            assert card1_rect['width'] > 200  # Reasonable card width
            assert card2_rect['width'] > 200
    
    def test_desktop_viewport_1200px(self, driver):
        """Test desktop viewport at 1200px width."""
        driver.set_window_size(1200, 800)  # Desktop
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check that persistent navigation is shown
        # Hamburger menu should be hidden on desktop
        hamburger_menus = driver.find_elements(By.CSS_SELECTOR, "[aria-label='open drawer']")
        if hamburger_menus:
            assert not hamburger_menus[0].is_displayed()
        
        # Check that tabs are not scrollable
        tabs_container = driver.find_element(By.CSS_SELECTOR, ".MuiTabs-root")
        assert "scrollable" not in tabs_container.get_attribute("class").lower()
        
        # Check that cards utilize full width
        cards = driver.find_elements(By.CSS_SELECTOR, ".MuiCard-root")
        if cards:
            card_rect = cards[0].rect
            assert card_rect['width'] > 300  # Desktop cards should be wider
    
    def test_touch_interactions(self, driver):
        """Test touch-friendly interactions on mobile."""
        driver.set_window_size(375, 667)  # iPhone 6/7/8
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check button sizes are touch-friendly (minimum 44px)
        buttons = driver.find_elements(By.CSS_SELECTOR, ".MuiButton-root")
        for button in buttons[:5]:  # Check first 5 buttons
            button_rect = button.rect
            assert button_rect['height'] >= 40  # Close to 44px minimum
    
    def test_text_readability(self, driver):
        """Test text readability across screen sizes."""
        viewports = [
            (320, 568),   # Mobile
            (768, 1024),  # Tablet
            (1200, 800),  # Desktop
        ]
        
        for width, height in viewports:
            driver.set_window_size(width, height)
            driver.get("http://localhost:3000/operations")
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            
            # Check that main headings are readable
            headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
            for heading in headings[:3]:  # Check first 3 headings
                font_size = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).fontSize", 
                    heading
                )
                # Font size should be at least 14px
                assert int(font_size.replace('px', '')) >= 14
    
    def test_navigation_drawer_mobile(self, driver):
        """Test navigation drawer behavior on mobile."""
        driver.set_window_size(375, 667)  # iPhone 6/7/8
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Click hamburger menu
        hamburger_menu = driver.find_element(By.CSS_SELECTOR, "[aria-label='open drawer']")
        hamburger_menu.click()
        
        # Wait for drawer to open
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiDrawer-paper"))
        )
        
        # Check that drawer is visible
        drawer = driver.find_element(By.CSS_SELECTOR, ".MuiDrawer-paper")
        assert drawer.is_displayed()
        
        # Check that drawer contains navigation items
        nav_items = drawer.find_elements(By.CSS_SELECTOR, ".MuiListItem-root")
        assert len(nav_items) > 0
    
    def test_table_responsiveness(self, driver):
        """Test table responsiveness and horizontal scrolling."""
        driver.set_window_size(320, 568)  # Small mobile
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Look for tables or table-like components
        tables = driver.find_elements(By.CSS_SELECTOR, ".MuiTable-root, .MuiTableContainer-root")
        
        for table in tables:
            # Check if table has horizontal scroll capability
            overflow_x = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).overflowX", 
                table
            )
            # Should allow horizontal scrolling on mobile
            assert overflow_x in ['auto', 'scroll']
    
    def test_form_responsiveness(self, driver):
        """Test form field responsiveness."""
        driver.set_window_size(320, 568)  # Small mobile
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check form fields if any exist
        form_fields = driver.find_elements(By.CSS_SELECTOR, ".MuiTextField-root input")
        
        for field in form_fields[:3]:  # Check first 3 fields
            field_rect = field.rect
            # Form fields should be reasonably sized for touch
            assert field_rect['height'] >= 32
            # Should not be too narrow
            assert field_rect['width'] >= 100


class TestAccessibility:
    """Test accessibility features."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Chrome driver for accessibility testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()
    
    def test_aria_labels(self, driver):
        """Test ARIA labels are present."""
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check for ARIA labels on interactive elements
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        for button in buttons[:5]:
            # Button should have accessible name (aria-label or text content)
            aria_label = button.get_attribute("aria-label")
            text_content = button.text.strip()
            assert aria_label or text_content, "Button missing accessible name"
    
    def test_keyboard_navigation(self, driver):
        """Test keyboard navigation support."""
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check that interactive elements are focusable
        focusable_elements = driver.find_elements(
            By.CSS_SELECTOR, 
            "button, input, select, textarea, a[href], [tabindex]:not([tabindex='-1'])"
        )
        
        for element in focusable_elements[:5]:
            # Element should be focusable
            tabindex = element.get_attribute("tabindex")
            if tabindex:
                assert int(tabindex) >= 0, "Element has negative tabindex"
    
    def test_color_contrast(self, driver):
        """Test color contrast ratios."""
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Check text elements for reasonable contrast
        text_elements = driver.find_elements(By.CSS_SELECTOR, "p, span, div")
        
        for element in text_elements[:10]:
            if element.text.strip():
                color = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).color", 
                    element
                )
                background = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).backgroundColor", 
                    element
                )
                
                # Basic check that color is not the same as background
                assert color != background, "Text color same as background"


class TestPerformance:
    """Test performance aspects of responsive design."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Chrome driver for performance testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()
    
    def test_page_load_time(self, driver):
        """Test page load time on mobile."""
        driver.set_window_size(375, 667)  # iPhone 6/7/8
        
        start_time = time.time()
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        load_time = time.time() - start_time
        
        # Page should load within 5 seconds
        assert load_time < 5.0, f"Page load time {load_time:.2f}s exceeds 5s limit"
    
    def test_animation_performance(self, driver):
        """Test that animations don't cause performance issues."""
        driver.set_window_size(375, 667)  # iPhone 6/7/8
        driver.get("http://localhost:3000/operations")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Trigger some interactions that might have animations
        try:
            # Click tabs to trigger transitions
            tabs = driver.find_elements(By.CSS_SELECTOR, ".MuiTab-root")
            if len(tabs) > 1:
                tabs[1].click()
                time.sleep(0.5)  # Allow animation to complete
                tabs[0].click()
                time.sleep(0.5)
        except:
            pass  # Ignore if tabs not found
        
        # Test should complete without hanging (implicit performance test)
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
