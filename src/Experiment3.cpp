#define _WIN32_WINNT 0x0600

#include <iostream>
#include <stdio.h>
#include <string.h>
#include <tchar.h>
#include <iomanip>	 
#include <Windows.h> 
#include <Tlhelp32.h>  
#include <shlwapi.h>
#include <Psapi.h>

#pragma comment(lib,"Shlwapi.lib") 
#pragma comment(lib, "Psapi.Lib")
#pragma comment(lib,"Kernel32.lib")

using namespace std;


enum ProgramState { 
    QUERY_SYS_INFO = 1,  
    QUERY_MEM_INFO,      
    QUERY_PRE_INFO,      
    EXIT                  
};

void getSystemInfo();
void getMemoryInfo();
void getProcessInfo();
void showSingleProcessMemDetail(int PID);
void help();

// Helper: Format bytes using ANSI version for CMD safety
inline void printStrFormatByte(const char* info, DWORDLONG bytes)
{
    char tmp[MAX_PATH];
    ZeroMemory(tmp, sizeof(tmp));
    StrFormatByteSizeA(bytes, tmp, MAX_PATH); // Use A (ANSI) version
    cout << info << tmp << endl;
}

// Print address in hex (CMD-friendly)
inline void printAddress(const char* info, LPVOID addr)
{
    // Save stream state
    ios::fmtflags oldFlags = cout.flags();
    char oldFill = cout.fill();
    
    cout << info << "0x"
         << hex << uppercase << setw(8) << setfill('0') << (uintptr_t)addr
         << dec << nouppercase;
    
    // Restore stream state
    cout.flags(oldFlags);
    cout.fill(oldFill);
    cout << endl;
}

inline void printDword(const char* info, DWORD dw)
{
    cout << info << dw << endl;
}

int main()
{
    setlocale(LC_ALL, "C"); // Ensure consistent ASCII behavior in CMD
    int state = 0;
    while (1)
    {
        help();
        cin >> state;
        cout << "\n";
        if (state == ProgramState::QUERY_SYS_INFO)  // 现在对应1
        {
            getSystemInfo();
        }
        else if (state == ProgramState::QUERY_MEM_INFO)  // 现在对应2
        {
            getMemoryInfo();
        }
        else if (state == ProgramState::QUERY_PRE_INFO)  // 现在对应3
        {
            getProcessInfo();

            cout << "Enter process PID to view its virtual memory info: ";
            int PID;
            cin >> PID;
            showSingleProcessMemDetail(PID);
        }
        else if (state == ProgramState::EXIT)  // 现在对应4
        {
            return 0;
        }
        else
        {
            cout << "Invalid option. Please try again.\n";
        }
    }
    return 0;
}

void getSystemInfo()
{
    SYSTEM_INFO si = {};
    GetNativeSystemInfo(&si);
    SIZE_T mem_size = (SIZE_T)si.lpMaximumApplicationAddress - (SIZE_T)si.lpMinimumApplicationAddress;

    printDword("Number of processors:          ", si.dwNumberOfProcessors);
    printStrFormatByte("Page size:                     ", si.dwPageSize);
    printAddress("Min application address:       ", si.lpMinimumApplicationAddress);
    printAddress("Max application address:       ", si.lpMaximumApplicationAddress);
    printStrFormatByte("Available address space:       ", (DWORDLONG)mem_size);
    cout << endl;
}

void getMemoryInfo()
{
    MEMORYSTATUSEX mem_stat = {};
    mem_stat.dwLength = sizeof(mem_stat);
    GlobalMemoryStatusEx(&mem_stat);

    cout << "Memory usage (%):              " << mem_stat.dwMemoryLoad << "%" << endl;
    printStrFormatByte("Total physical memory:         ", mem_stat.ullTotalPhys);
    printStrFormatByte("Available physical memory:     ", mem_stat.ullAvailPhys);
    printStrFormatByte("Total page file:               ", mem_stat.ullTotalPageFile);
    printStrFormatByte("Available page file:           ", mem_stat.ullAvailPageFile);
    printStrFormatByte("Total virtual memory:          ", mem_stat.ullTotalVirtual);
    printStrFormatByte("Available virtual memory:      ", mem_stat.ullAvailVirtual);
    printStrFormatByte("Available extended memory:     ", mem_stat.ullAvailExtendedVirtual);
    cout << endl;

    PERFORMANCE_INFORMATION pi = {};
    if (GetPerformanceInfo(&pi, sizeof(pi)))
    {
        DWORDLONG page_size = pi.PageSize;
        printStrFormatByte("Commit Total:                  ", pi.CommitTotal * page_size);
        printStrFormatByte("Commit Limit:                  ", pi.CommitLimit * page_size);
        printStrFormatByte("Commit Peak:                   ", pi.CommitPeak * page_size);
        printStrFormatByte("Physical Memory (Total):       ", pi.PhysicalTotal * page_size);
        printStrFormatByte("Physical Memory (Available):   ", pi.PhysicalAvailable * page_size);
        printStrFormatByte("System Cache:                  ", pi.SystemCache * page_size);
        printStrFormatByte("Kernel Total:                  ", pi.KernelTotal * page_size);
        printStrFormatByte("Kernel Paged:                  ", pi.KernelPaged * page_size);
        printStrFormatByte("Kernel Nonpaged:               ", pi.KernelNonpaged * page_size);
        printDword("Handle Count:                  ", pi.HandleCount);
        printDword("Process Count:                 ", pi.ProcessCount);
        printDword("Thread Count:                  ", pi.ThreadCount);
    }
    cout << endl;
}

void getProcessInfo()
{
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE)
    {
        cout << "Failed to create process snapshot.\n";
        return;
    }

    PROCESSENTRY32 pe = {};
    pe.dwSize = sizeof(pe);

    // Ensure cout is in a clean state
    ios::fmtflags oldFlags = cout.flags();
    char oldFill = cout.fill();
    
    cout << left << setw(30) << "Process Name"
         << right << setw(10) << "PID"
         << setw(10) << "Threads" << endl;
    cout << string(55, '-') << endl;

    if (Process32First(hSnap, &pe))
    {
        do
        {
            // Ensure null termination
            pe.szExeFile[MAX_PATH - 1] = '\0';

            // Replace non-printable or control characters with '?'
            for (int i = 0; pe.szExeFile[i] != '\0'; ++i)
            {
                unsigned char c = (unsigned char)pe.szExeFile[i];
                if (c < 32 || c > 126)
                    pe.szExeFile[i] = '?';
            }

            cout << left << setw(30) << pe.szExeFile
                 << right << setw(10) << pe.th32ProcessID
                 << setw(10) << pe.cntThreads << endl;

        } while (Process32Next(hSnap, &pe));
    }
    else
    {
        cout << "No processes found.\n";
    }

    // Restore cout state
    cout.flags(oldFlags);
    cout.fill(oldFill);
    
    CloseHandle(hSnap);
    cout << endl;
}

void printPageProtection(DWORD dwProtect)
{
    const int width = 20;
    DWORD base = dwProtect & 0xFF; // Ignore PAGE_GUARD, PAGE_NOCACHE flags

    switch (base)
    {
    case PAGE_NOACCESS:          cout << left << setw(width) << "NOACCESS"; break;
    case PAGE_READONLY:          cout << left << setw(width) << "READONLY"; break;
    case PAGE_READWRITE:         cout << left << setw(width) << "READWRITE"; break;
    case PAGE_WRITECOPY:         cout << left << setw(width) << "WRITECOPY"; break;
    case PAGE_EXECUTE:           cout << left << setw(width) << "EXECUTE"; break;
    case PAGE_EXECUTE_READ:      cout << left << setw(width) << "EXECUTE_READ"; break;
    case PAGE_EXECUTE_READWRITE: cout << left << setw(width) << "EXECUTE_READWRITE"; break;
    case PAGE_EXECUTE_WRITECOPY: cout << left << setw(width) << "EXECUTE_WRITECOPY"; break;
    default:                     cout << left << setw(width) << "UNKNOWN"; break;
    }
}

void showSingleProcessMemDetail(int PID)
{
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, PID);
    if (!hProcess)
    {
        cout << "Failed to open process (PID=" << PID << "). Access denied or invalid.\n\n";
        return;
    }

    SYSTEM_INFO si = {};
    GetSystemInfo(&si);

    LPCVOID addr = si.lpMinimumApplicationAddress;

    cout << left
         << setw(20) << "Base Address"
         << setw(12) << "Region Size"
         << setw(12) << "State"
         << setw(20) << "Protection"
         << "Type" << endl;
    cout << string(75, '-') << endl;

    MEMORY_BASIC_INFORMATION mbi = {};
    while (addr < si.lpMaximumApplicationAddress)
    {
        if (VirtualQueryEx(hProcess, addr, &mbi, sizeof(mbi)) != sizeof(mbi))
            break;

        // Save stream state before hex formatting
        ios::fmtflags oldFlags = cout.flags();
        char oldFill = cout.fill();
        
        // Base Address
        cout << "0x" << hex << uppercase << setw(8) << setfill('0') 
             << (uintptr_t)mbi.BaseAddress;
        
        // Restore immediately after hex output
        cout.flags(oldFlags);
        cout.fill(oldFill);
        
        // Region Size
        char sizeBuf[32];
        StrFormatByteSizeA(mbi.RegionSize, sizeBuf, sizeof(sizeBuf));
        cout << "  " << left << setw(10) << sizeBuf;

        // State
        if (mbi.State == MEM_COMMIT)      cout << "  COMMIT    ";
        else if (mbi.State == MEM_RESERVE) cout << "  RESERVE   ";
        else if (mbi.State == MEM_FREE)    cout << "  FREE      ";
        else                              cout << "  ???       ";

        // Protection
        if (mbi.State != MEM_FREE)
            printPageProtection(mbi.Protect);
        else
            cout << "N/A                 ";

        // Type
        if (mbi.Type == MEM_IMAGE)    cout << "  Image";
        else if (mbi.Type == MEM_MAPPED) cout << "  Mapped";
        else if (mbi.Type == MEM_PRIVATE) cout << "  Private";
        else                          cout << "  Unknown";

        cout << endl;

        // Next region
        addr = (BYTE*)mbi.BaseAddress + mbi.RegionSize;
        if (mbi.RegionSize == 0) break; // Safety
    }

    CloseHandle(hProcess);
    cout << endl;
}

void help()
{
    cout << "\n\n=== System Info Tool ===\n";
    // 显示1-4而不是0-3
    cout << ProgramState::QUERY_SYS_INFO << " - Show system information\n";
    cout << ProgramState::QUERY_MEM_INFO << " - Show memory usage\n";
    cout << ProgramState::QUERY_PRE_INFO << " - List processes and inspect by PID\n";
    cout << ProgramState::EXIT << " - Exit\n";
    cout << "\nChoose an option (1-4): ";  // 修改提示信息
}