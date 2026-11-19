// stack_test.c
#include <stdio.h>

int main() {
    unsigned long original_rsp, new_rsp;
    unsigned long value = 0xDEADBEEF;

    // 保存当前栈指针
    asm volatile ("movq %%rsp, %0" : "=r"(original_rsp));

    printf("Before push: rsp = 0x%lx\n", original_rsp);

    // 压栈
    asm volatile ("pushq %0" :: "r"(value));
    
    asm volatile ("movq %%rsp, %0" : "=r"(new_rsp));
    printf("After push:  rsp = 0x%lx (delta = %ld)\n", new_rsp, original_rsp - new_rsp);

    // 出栈（存入 dummy）
    unsigned long popped;
    asm volatile ("popq %0" : "=r"(popped));
    printf("Popped value: 0x%lx\n", popped);

    return 0;
}