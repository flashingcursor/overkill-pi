"""Terminal User Interface framework for OVERKILL"""

import curses
from typing import List, Optional, Callable, Tuple, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from ..core.logger import logger


@dataclass
class MenuItem:
    """Menu item definition"""
    label: str
    action: Optional[Callable] = None
    submenu: Optional[List['MenuItem']] = None
    data: Any = None


class Colors:
    """Color pairs for the TUI"""
    DEFAULT = 0
    HEADER = 1
    MENU = 2
    SELECTED = 3
    ERROR = 4
    SUCCESS = 5
    WARNING = 6
    INFO = 7


class BaseWidget(ABC):
    """Base class for TUI widgets"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.window = None
        self.height = 0
        self.width = 0
        self.y = 0
        self.x = 0
    
    @abstractmethod
    def draw(self):
        """Draw the widget"""
        pass
    
    def refresh(self):
        """Refresh the widget"""
        if self.window:
            self.window.refresh()


class OverkillTUI:
    """Main TUI class with curses interface"""
    
    def __init__(self):
        self.stdscr = None
        self.colors_enabled = False
        self.current_menu = []
        self.menu_stack = []
        
    def init_colors(self):
        """Initialize color pairs"""
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # Define color pairs
            curses.init_pair(Colors.HEADER, curses.COLOR_RED, -1)
            curses.init_pair(Colors.MENU, curses.COLOR_CYAN, -1)
            curses.init_pair(Colors.SELECTED, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(Colors.ERROR, curses.COLOR_RED, -1)
            curses.init_pair(Colors.SUCCESS, curses.COLOR_GREEN, -1)
            curses.init_pair(Colors.WARNING, curses.COLOR_YELLOW, -1)
            curses.init_pair(Colors.INFO, curses.COLOR_CYAN, -1)
            
            self.colors_enabled = True
    
    def run(self, main_func: Callable):
        """Run the TUI application"""
        try:
            curses.wrapper(self._run, main_func)
        except KeyboardInterrupt:
            logger.info("TUI interrupted by user")
        except Exception as e:
            logger.error(f"TUI error: {e}")
            raise
    
    def _run(self, stdscr, main_func):
        """Internal run method with curses wrapper"""
        self.stdscr = stdscr
        
        # Configure curses
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)  # Enable special keys
        stdscr.timeout(100)  # Non-blocking input with 100ms timeout
        
        # Initialize colors
        self.init_colors()
        
        # Clear screen
        stdscr.clear()
        
        # Run main function
        main_func(self)
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Get terminal dimensions"""
        if self.stdscr:
            return self.stdscr.getmaxyx()
        return 24, 80  # Default fallback
    
    def draw_header(self):
        """Draw OVERKILL ASCII art header"""
        if not self.stdscr:
            return
        
        self.stdscr.clear()
        height, width = self.get_dimensions()
        
        # ASCII art header
        header_lines = [
            "        ....            _                                       ..         .          ..       .. ",
            "    .x~X88888Hx.       u                                  < .z@8\"`        @88>  x .d88\"  x .d88\"  ",
            "   H8X 888888888h.    88Nu.   u.                .u    .    !@88E          %8P    5888R    5888R   ",
            "  8888:`*888888888:  '88888.o888c      .u     .d88B :@8c   '888E   u       .     '888R    '888R   ",
            "  88888:        `%8   ^8888  8888   ud8888.  =\"8888f8888r   888E u@8NL   .@88u    888R     888R   ",
            ". `88888          ?>   8888  8888 :888'8888.   4888>'88\"    888E`\"88*\"  ''888E`   888R     888R   ",
            "`. ?888%           X   8888  8888 d888 '88%\"   4888> '      888E .dN.     888E    888R     888R   ",
            "  ~*??.            >   8888  8888 8888.+\"      4888>        888E~8888     888E    888R     888R   ",
            " .x88888h.        <   .8888b.888P 8888L       .d888L .+     888E '888&    888E    888R     888R   ",
            ":\"\"\"8888888x..  .x     ^Y8888*\"\"  '8888c. .+  ^\"8888*\"      888E  9888.   888&   .888B .  .888B . ",
            "`    `*888888888\"        `Y\"       \"88888%       \"Y\"      '\"888*\" 4888\"   R888\"  ^*888%   ^*888%  ",
            "        \"\"***\"\"                      \"YP'                    \"\"    \"\"      \"\"      \"%       \"%    "
        ]
        
        # Calculate starting position for centered header
        header_height = len(header_lines)
        header_width = max(len(line) for line in header_lines)
        
        start_y = 1
        
        # Draw header with color
        for i, line in enumerate(header_lines):
            if start_y + i < height - 2:  # Leave room for subtitle
                # Center each line
                start_x = max(0, (width - len(line)) // 2)
                try:
                    if self.colors_enabled:
                        self.stdscr.attron(curses.color_pair(Colors.HEADER))
                    self.stdscr.addstr(start_y + i, start_x, line[:width-1])
                    if self.colors_enabled:
                        self.stdscr.attroff(curses.color_pair(Colors.HEADER))
                except curses.error:
                    pass
        
        # Draw subtitle
        subtitle = "Raspberry Pi 5 Media Center Configuration"
        subtitle_y = start_y + header_height + 1
        if subtitle_y < height - 1:
            subtitle_x = max(0, (width - len(subtitle)) // 2)
            try:
                if self.colors_enabled:
                    self.stdscr.attron(curses.color_pair(Colors.INFO))
                self.stdscr.addstr(subtitle_y, subtitle_x, subtitle)
                if self.colors_enabled:
                    self.stdscr.attroff(curses.color_pair(Colors.INFO))
            except curses.error:
                pass
    
    def draw_box(self, y: int, x: int, height: int, width: int, title: str = ""):
        """Draw a box with optional title"""
        if not self.stdscr:
            return
        
        max_height, max_width = self.get_dimensions()
        
        # Ensure box fits in screen
        height = min(height, max_height - y)
        width = min(width, max_width - x)
        
        if height < 3 or width < 3:
            return
        
        try:
            # Draw corners
            self.stdscr.addch(y, x, curses.ACS_ULCORNER)
            self.stdscr.addch(y, x + width - 1, curses.ACS_URCORNER)
            self.stdscr.addch(y + height - 1, x, curses.ACS_LLCORNER)
            self.stdscr.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER)
            
            # Draw horizontal lines
            for i in range(1, width - 1):
                self.stdscr.addch(y, x + i, curses.ACS_HLINE)
                self.stdscr.addch(y + height - 1, x + i, curses.ACS_HLINE)
            
            # Draw vertical lines
            for i in range(1, height - 1):
                self.stdscr.addch(y + i, x, curses.ACS_VLINE)
                self.stdscr.addch(y + i, x + width - 1, curses.ACS_VLINE)
            
            # Draw title if provided
            if title:
                title = f" {title} "
                title_x = x + (width - len(title)) // 2
                if title_x > x and title_x + len(title) < x + width:
                    self.stdscr.attron(curses.A_BOLD)
                    self.stdscr.addstr(y, title_x, title)
                    self.stdscr.attroff(curses.A_BOLD)
        
        except curses.error:
            pass
    
    def menu(self, title: str, items: List[str], selected: int = 0) -> Optional[int]:
        """
        Display a menu and get selection
        
        Args:
            title: Menu title
            items: List of menu items
            selected: Initially selected item
        
        Returns:
            Selected index or None if cancelled
        """
        if not self.stdscr or not items:
            return None
        
        self.draw_header()
        height, width = self.get_dimensions()
        
        # Calculate menu dimensions
        menu_width = min(max(len(title) + 4, max(len(item) for item in items) + 6), width - 4)
        menu_height = min(len(items) + 4, height - 15)  # Leave room for header
        
        # Calculate position (centered)
        menu_y = max(14, (height - menu_height) // 2)
        menu_x = (width - menu_width) // 2
        
        current_selection = selected
        
        while True:
            # Draw menu box
            self.draw_box(menu_y, menu_x, menu_height, menu_width, title)
            
            # Draw menu items
            visible_items = min(len(items), menu_height - 4)
            scroll_offset = max(0, current_selection - visible_items + 1)
            
            for i in range(visible_items):
                item_index = i + scroll_offset
                if item_index >= len(items):
                    break
                
                item = items[item_index]
                y = menu_y + 2 + i
                x = menu_x + 2
                
                # Truncate item if too long
                max_item_width = menu_width - 4
                if len(item) > max_item_width:
                    item = item[:max_item_width-3] + "..."
                
                try:
                    if item_index == current_selection:
                        # Highlight selected item
                        if self.colors_enabled:
                            self.stdscr.attron(curses.color_pair(Colors.SELECTED))
                        self.stdscr.addstr(y, x, f"> {item:<{max_item_width-2}}")
                        if self.colors_enabled:
                            self.stdscr.attroff(curses.color_pair(Colors.SELECTED))
                    else:
                        self.stdscr.addstr(y, x, f"  {item}")
                except curses.error:
                    pass
            
            # Draw scroll indicators
            if scroll_offset > 0:
                self.stdscr.addstr(menu_y + 1, menu_x + menu_width - 3, "↑")
            if scroll_offset + visible_items < len(items):
                self.stdscr.addstr(menu_y + menu_height - 2, menu_x + menu_width - 3, "↓")
            
            # Draw help text
            help_y = menu_y + menu_height + 1
            if help_y < height - 1:
                help_text = "↑↓: Navigate | Enter: Select | ESC/q: Cancel"
                help_x = (width - len(help_text)) // 2
                try:
                    self.stdscr.addstr(help_y, help_x, help_text)
                except curses.error:
                    pass
            
            self.stdscr.refresh()
            
            # Handle input
            key = self.stdscr.getch()
            
            if key == curses.KEY_UP:
                current_selection = (current_selection - 1) % len(items)
            elif key == curses.KEY_DOWN:
                current_selection = (current_selection + 1) % len(items)
            elif key == ord('\n') or key == curses.KEY_ENTER:
                return current_selection
            elif key == 27 or key == ord('q') or key == ord('Q'):  # ESC or q
                return None
    
    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """Show a message dialog"""
        if not self.stdscr:
            return
        
        self.draw_header()
        height, width = self.get_dimensions()
        
        # Split message into lines
        lines = message.strip().split('\n')
        max_line_width = max(len(line) for line in lines)
        
        # Calculate dialog dimensions
        dialog_width = min(max(len(title) + 4, max_line_width + 4, 40), width - 4)
        dialog_height = min(len(lines) + 5, height - 15)
        
        # Calculate position
        dialog_y = (height - dialog_height) // 2
        dialog_x = (width - dialog_width) // 2
        
        # Draw dialog box
        self.draw_box(dialog_y, dialog_x, dialog_height, dialog_width, title)
        
        # Determine color based on message type
        color = Colors.INFO
        if msg_type == "error":
            color = Colors.ERROR
        elif msg_type == "success":
            color = Colors.SUCCESS
        elif msg_type == "warning":
            color = Colors.WARNING
        
        # Draw message lines
        for i, line in enumerate(lines[:dialog_height-4]):
            y = dialog_y + 2 + i
            x = dialog_x + 2
            
            # Truncate line if needed
            max_width = dialog_width - 4
            if len(line) > max_width:
                line = line[:max_width-3] + "..."
            
            try:
                if self.colors_enabled:
                    self.stdscr.attron(curses.color_pair(color))
                self.stdscr.addstr(y, x, line)
                if self.colors_enabled:
                    self.stdscr.attroff(curses.color_pair(color))
            except curses.error:
                pass
        
        # Draw "Press any key" message
        press_key_msg = "Press any key to continue"
        press_key_y = dialog_y + dialog_height - 2
        press_key_x = dialog_x + (dialog_width - len(press_key_msg)) // 2
        
        try:
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(press_key_y, press_key_x, press_key_msg)
            self.stdscr.attroff(curses.A_BOLD)
        except curses.error:
            pass
        
        self.stdscr.refresh()
        
        # Wait for key press
        self.stdscr.timeout(-1)  # Blocking mode
        self.stdscr.getch()
        self.stdscr.timeout(100)  # Back to non-blocking
    
    def show_info(self, title: str, message: str):
        """Show info message"""
        self.show_message(title, message, "info")
    
    def show_error(self, title: str, message: str):
        """Show error message"""
        self.show_message(title, message, "error")
    
    def show_success(self, title: str, message: str):
        """Show success message"""
        self.show_message(title, message, "success")
    
    def show_warning(self, title: str, message: str):
        """Show warning message"""
        self.show_message(title, message, "warning")
    
    def confirm(self, title: str, message: str) -> bool:
        """Show confirmation dialog"""
        options = ["Yes", "No"]
        result = self.menu(f"{title} - {message}", options, selected=1)
        return result == 0 if result is not None else False