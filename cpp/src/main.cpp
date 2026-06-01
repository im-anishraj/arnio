#include <iostream>
#include <string>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

int get_terminal_width() {
#ifdef _WIN32
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    int columns;
    GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &csbi);
    columns = csbi.srWindow.Right - csbi.srWindow.Left + 1;
    return columns;
#else
    struct winsize w;
    ioctl(STDOUT_FILENO, TIOCGWINSZ, &w);
    return w.ws_col;
#endif
}

void show_menu() {
    int width = get_terminal_width();

    if (width < 60) {
        // "Mobile view"
        std::cout << "\n[1]Shape [2]Cols [3]Desc [4]Exit\n";
    } else {
        // "Desktop view"
        std::cout << "\n===== ARNIO FRAME MENU =====\n";
        std::cout << "1. Show Frame Shape\n";
        std::cout << "2. List Columns\n";
        std::cout << "3. Describe Frame\n";
        std::cout << "4. Exit\n";
        std::cout << "============================\n";
    }
}
