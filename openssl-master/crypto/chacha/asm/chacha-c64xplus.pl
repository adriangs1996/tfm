#! /usr/bin/env perl
# Copyright 2016-2020 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

#
# ====================================================================
# Written by Andy Polyakov <appro@openssl.org> for the OpenSSL
# project. The module is, however, dual licensed under OpenSSL and
# CRYPTOGAMS licenses depending on where you obtain it. For further
# details see http://www.openssl.org/~appro/cryptogams/.
# ====================================================================
#
# ChaCha20 for C64x+.
#
# October 2015
#
# Performance is 3.54 cycles per processed byte, which is ~4.3 times
# faster than code generated by TI compiler. Compiler also disables
# interrupts for some reason, thus making interrupt response time
# dependent on input length. This module on the other hand is free
# from such limitation.

$output=pop and open STDOUT,">$output";

($OUT,$INP,$LEN,$KEYB,$COUNTERA)=("A4","B4","A6","B6","A8");
($KEYA,$COUNTERB,$STEP)=("A7","B7","A3");

@X=  ("A16","B16","A17","B17","A18","B18","A19","B19",
      "A20","B20","A21","B21","A22","B22","A23","B23");
@Y=  ("A24","B24","A25","B25","A26","B26","A27","B27",
      "A28","B28","A29","B29","A30","B30","A31","B31");
@DAT=("A6", "A7", "B6", "B7", "A8", "A9", "B8", "B9",
      "A10","A11","B10","B11","A12","A13","B12","B13");

# yes, overlaps with @DAT, used only in 2x interleave code path...
@K2x=("A6", "B6", "A7", "B7", "A8", "B8", "A9", "B9",
      "A10","B10","A11","B11","A2", "B2", "A13","B13");

$code.=<<___;
	.text

	.if	.ASSEMBLER_VERSION<7000000
	.asg	0,__TI_EABI__
	.endif
	.if	__TI_EABI__
	.asg	ChaCha20_ctr32,_ChaCha20_ctr32
	.endif

	.asg	B3,RA
	.asg	A15,FP
	.asg	B15,SP

	.global	_ChaCha20_ctr32
	.align	32
_ChaCha20_ctr32:
	.asmfunc	stack_usage(40+64)
	MV	$LEN,A0			; reassign
  [!A0]	BNOP	RA			; no data
|| [A0]	STW	FP,*SP--(40+64)		; save frame pointer and alloca(40+64)
|| [A0]	MV	SP,FP
   [A0]	STDW	B13:B12,*SP[4+8]	; ABI says so
|| [A0]	MV	$KEYB,$KEYA
|| [A0]	MV	$COUNTERA,$COUNTERB
   [A0]	STDW	B11:B10,*SP[3+8]
|| [A0]	STDW	A13:A12,*FP[-3]
   [A0]	STDW	A11:A10,*FP[-4]
|| [A0]	MVK	128,$STEP		; 2 * input block size

   [A0]	LDW	*${KEYA}[0],@Y[4]	; load key
|| [A0]	LDW	*${KEYB}[1],@Y[5]
|| [A0]	MVK	0x00007865,@Y[0]	; synthesize sigma
|| [A0]	MVK	0x0000646e,@Y[1]
   [A0]	LDW	*${KEYA}[2],@Y[6]
|| [A0]	LDW	*${KEYB}[3],@Y[7]
|| [A0]	MVKH	0x61700000,@Y[0]
|| [A0]	MVKH	0x33200000,@Y[1]
	LDW	*${KEYA}[4],@Y[8]
||	LDW	*${KEYB}[5],@Y[9]
||	MVK	0x00002d32,@Y[2]
||	MVK	0x00006574,@Y[3]
	LDW	*${KEYA}[6],@Y[10]
||	LDW	*${KEYB}[7],@Y[11]
||	MVKH	0x79620000,@Y[2]
||	MVKH	0x6b200000,@Y[3]
	LDW	*${COUNTERA}[0],@Y[12]	; load counter||nonce
||	LDW	*${COUNTERB}[1],@Y[13]
||	CMPLTU	A0,$STEP,A1		; is length < 2*blocks?
	LDW	*${COUNTERA}[2],@Y[14]
||	LDW	*${COUNTERB}[3],@Y[15]
|| [A1]	BNOP	top1x?
   [A1]	MVK	64,$STEP		; input block size
||	MVK	10,B0			; inner loop counter

	DMV	@Y[2],@Y[0],@X[2]:@X[0]	; copy block
||	DMV	@Y[3],@Y[1],@X[3]:@X[1]
||[!A1]	STDW	@Y[2]:@Y[0],*FP[-12]	; offload key material to stack
||[!A1]	STDW	@Y[3]:@Y[1],*SP[2]
	DMV	@Y[6],@Y[4],@X[6]:@X[4]
||	DMV	@Y[7],@Y[5],@X[7]:@X[5]
||[!A1]	STDW	@Y[6]:@Y[4],*FP[-10]
||[!A1]	STDW	@Y[7]:@Y[5],*SP[4]
	DMV	@Y[10],@Y[8],@X[10]:@X[8]
||	DMV	@Y[11],@Y[9],@X[11]:@X[9]
||[!A1]	STDW	@Y[10]:@Y[8],*FP[-8]
||[!A1]	STDW	@Y[11]:@Y[9],*SP[6]
	DMV	@Y[14],@Y[12],@X[14]:@X[12]
||	DMV	@Y[15],@Y[13],@X[15]:@X[13]
||[!A1]	MV	@Y[12],@K2x[12]		; counter
||[!A1]	MV	@Y[13],@K2x[13]
||[!A1]	STW	@Y[14],*FP[-6*2]
||[!A1]	STW	@Y[15],*SP[8*2]
___
{	################################################################
	# 2x interleave gives 50% performance improvement
	#
my ($a0,$a1,$a2,$a3) = (0..3);
my ($b0,$b1,$b2,$b3) = (4..7);
my ($c0,$c1,$c2,$c3) = (8..11);
my ($d0,$d1,$d2,$d3) = (12..15);

$code.=<<___;
outer2x?:
	ADD	@X[$b1],@X[$a1],@X[$a1]
||	ADD	@X[$b2],@X[$a2],@X[$a2]
||	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	 DMV	@Y[2],@Y[0],@K2x[2]:@K2x[0]
||	 DMV	@Y[3],@Y[1],@K2x[3]:@K2x[1]
	XOR	@X[$a1],@X[$d1],@X[$d1]
||	XOR	@X[$a2],@X[$d2],@X[$d2]
||	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	 DMV	@Y[6],@Y[4],@K2x[6]:@K2x[4]
||	 DMV	@Y[7],@Y[5],@K2x[7]:@K2x[5]
	SWAP2	@X[$d1],@X[$d1]		; rotate by 16
||	SWAP2	@X[$d2],@X[$d2]
||	SWAP2	@X[$d0],@X[$d0]
||	SWAP2	@X[$d3],@X[$d3]

	ADD	@X[$d1],@X[$c1],@X[$c1]
||	ADD	@X[$d2],@X[$c2],@X[$c2]
||	ADD	@X[$d0],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c3],@X[$c3]
||	 DMV	@Y[10],@Y[8],@K2x[10]:@K2x[8]
||	 DMV	@Y[11],@Y[9],@K2x[11]:@K2x[9]
	XOR	@X[$c1],@X[$b1],@X[$b1]
||	XOR	@X[$c2],@X[$b2],@X[$b2]
||	XOR	@X[$c0],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b3],@X[$b3]
||	 ADD	1,@Y[12],@Y[12]		; adjust counter for 2nd block
	ROTL	@X[$b1],12,@X[$b1]
||	ROTL	@X[$b2],12,@X[$b2]
||	 MV	@Y[14],@K2x[14]
||	 MV	@Y[15],@K2x[15]
top2x?:
	ROTL	@X[$b0],12,@X[$b0]
||	ROTL	@X[$b3],12,@X[$b3]
||	 ADD	@Y[$b1],@Y[$a1],@Y[$a1]
||	 ADD	@Y[$b2],@Y[$a2],@Y[$a2]
	 ADD	@Y[$b0],@Y[$a0],@Y[$a0]
||	 ADD	@Y[$b3],@Y[$a3],@Y[$a3]

||	ADD	@X[$b1],@X[$a1],@X[$a1]
||	ADD	@X[$b2],@X[$a2],@X[$a2]
||	 XOR	@Y[$a1],@Y[$d1],@Y[$d1]
||	 XOR	@Y[$a2],@Y[$d2],@Y[$d2]
	 XOR	@Y[$a0],@Y[$d0],@Y[$d0]
||	 XOR	@Y[$a3],@Y[$d3],@Y[$d3]
||	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
||	XOR	@X[$a2],@X[$d2],@X[$d2]
	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	ROTL	@X[$d1],8,@X[$d1]
||	ROTL	@X[$d2],8,@X[$d2]
||	 SWAP2	@Y[$d1],@Y[$d1]		; rotate by 16
||	 SWAP2	@Y[$d2],@Y[$d2]
||	 SWAP2	@Y[$d0],@Y[$d0]
||	 SWAP2	@Y[$d3],@Y[$d3]
	ROTL	@X[$d0],8,@X[$d0]
||	ROTL	@X[$d3],8,@X[$d3]
||	 ADD	@Y[$d1],@Y[$c1],@Y[$c1]
||	 ADD	@Y[$d2],@Y[$c2],@Y[$c2]
||	 ADD	@Y[$d0],@Y[$c0],@Y[$c0]
||	 ADD	@Y[$d3],@Y[$c3],@Y[$c3]
||	BNOP	middle2x1?		; protect from interrupt

	ADD	@X[$d1],@X[$c1],@X[$c1]
||	ADD	@X[$d2],@X[$c2],@X[$c2]
||	 XOR	@Y[$c1],@Y[$b1],@Y[$b1]
||	 XOR	@Y[$c2],@Y[$b2],@Y[$b2]
||	 XOR	@Y[$c0],@Y[$b0],@Y[$b0]
||	 XOR	@Y[$c3],@Y[$b3],@Y[$b3]
	ADD	@X[$d0],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c3],@X[$c3]
||	XOR	@X[$c1],@X[$b1],@X[$b1]
||	XOR	@X[$c2],@X[$b2],@X[$b2]
||	ROTL	@X[$d1],0,@X[$d2]	; moved to avoid cross-path stall
||	ROTL	@X[$d2],0,@X[$d3]
	XOR	@X[$c0],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b3],@X[$b3]
||	MV	@X[$d0],@X[$d1]
||	MV	@X[$d3],@X[$d0]
||	 ROTL	@Y[$b1],12,@Y[$b1]
||	 ROTL	@Y[$b2],12,@Y[$b2]
	ROTL	@X[$b1],7,@X[$b0]	; avoided cross-path stall
||	ROTL	@X[$b2],7,@X[$b1]
	ROTL	@X[$b0],7,@X[$b3]
||	ROTL	@X[$b3],7,@X[$b2]
middle2x1?:

	 ROTL	@Y[$b0],12,@Y[$b0]
||	 ROTL	@Y[$b3],12,@Y[$b3]
||	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b1],@X[$a1],@X[$a1]
	ADD	@X[$b2],@X[$a2],@X[$a2]
||	ADD	@X[$b3],@X[$a3],@X[$a3]

||	 ADD	@Y[$b1],@Y[$a1],@Y[$a1]
||	 ADD	@Y[$b2],@Y[$a2],@Y[$a2]
||	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
	XOR	@X[$a2],@X[$d2],@X[$d2]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	 ADD	@Y[$b0],@Y[$a0],@Y[$a0]
||	 ADD	@Y[$b3],@Y[$a3],@Y[$a3]
||	 XOR	@Y[$a1],@Y[$d1],@Y[$d1]
||	 XOR	@Y[$a2],@Y[$d2],@Y[$d2]
	 XOR	@Y[$a0],@Y[$d0],@Y[$d0]
||	 XOR	@Y[$a3],@Y[$d3],@Y[$d3]
||	 ROTL	@Y[$d1],8,@Y[$d1]
||	 ROTL	@Y[$d2],8,@Y[$d2]
||	SWAP2	@X[$d0],@X[$d0]		; rotate by 16
||	SWAP2	@X[$d1],@X[$d1]
||	SWAP2	@X[$d2],@X[$d2]
||	SWAP2	@X[$d3],@X[$d3]
	 ROTL	@Y[$d0],8,@Y[$d0]
||	 ROTL	@Y[$d3],8,@Y[$d3]
||	ADD	@X[$d0],@X[$c2],@X[$c2]
||	ADD	@X[$d1],@X[$c3],@X[$c3]
||	ADD	@X[$d2],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c1],@X[$c1]
||	BNOP	middle2x2?		; protect from interrupt

	 ADD	@Y[$d1],@Y[$c1],@Y[$c1]
||	 ADD	@Y[$d2],@Y[$c2],@Y[$c2]
||	XOR	@X[$c2],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b1],@X[$b1]
||	XOR	@X[$c0],@X[$b2],@X[$b2]
||	XOR	@X[$c1],@X[$b3],@X[$b3]
	 ADD	@Y[$d0],@Y[$c0],@Y[$c0]
||	 ADD	@Y[$d3],@Y[$c3],@Y[$c3]
||	 XOR	@Y[$c1],@Y[$b1],@Y[$b1]
||	 XOR	@Y[$c2],@Y[$b2],@Y[$b2]
||	 ROTL	@Y[$d1],0,@Y[$d2]	; moved to avoid cross-path stall
||	 ROTL	@Y[$d2],0,@Y[$d3]
	 XOR	@Y[$c0],@Y[$b0],@Y[$b0]
||	 XOR	@Y[$c3],@Y[$b3],@Y[$b3]
||	 MV	@Y[$d0],@Y[$d1]
||	 MV	@Y[$d3],@Y[$d0]
||	ROTL	@X[$b0],12,@X[$b0]
||	ROTL	@X[$b1],12,@X[$b1]
	 ROTL	@Y[$b1],7,@Y[$b0]	; avoided cross-path stall
||	 ROTL	@Y[$b2],7,@Y[$b1]
	 ROTL	@Y[$b0],7,@Y[$b3]
||	 ROTL	@Y[$b3],7,@Y[$b2]
middle2x2?:

	ROTL	@X[$b2],12,@X[$b2]
||	ROTL	@X[$b3],12,@X[$b3]
||	 ADD	@Y[$b0],@Y[$a0],@Y[$a0]
||	 ADD	@Y[$b1],@Y[$a1],@Y[$a1]
	 ADD	@Y[$b2],@Y[$a2],@Y[$a2]
||	 ADD	@Y[$b3],@Y[$a3],@Y[$a3]

||	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b1],@X[$a1],@X[$a1]
||	 XOR	@Y[$a0],@Y[$d0],@Y[$d0]
||	 XOR	@Y[$a1],@Y[$d1],@Y[$d1]
	 XOR	@Y[$a2],@Y[$d2],@Y[$d2]
||	 XOR	@Y[$a3],@Y[$d3],@Y[$d3]
||	ADD	@X[$b2],@X[$a2],@X[$a2]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
	XOR	@X[$a2],@X[$d2],@X[$d2]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	ROTL	@X[$d0],8,@X[$d0]
||	ROTL	@X[$d1],8,@X[$d1]
||	 SWAP2	@Y[$d0],@Y[$d0]		; rotate by 16
||	 SWAP2	@Y[$d1],@Y[$d1]
||	 SWAP2	@Y[$d2],@Y[$d2]
||	 SWAP2	@Y[$d3],@Y[$d3]
	ROTL	@X[$d2],8,@X[$d2]
||	ROTL	@X[$d3],8,@X[$d3]
||	 ADD	@Y[$d0],@Y[$c2],@Y[$c2]
||	 ADD	@Y[$d1],@Y[$c3],@Y[$c3]
||	 ADD	@Y[$d2],@Y[$c0],@Y[$c0]
||	 ADD	@Y[$d3],@Y[$c1],@Y[$c1]
||	BNOP	bottom2x1?		; protect from interrupt

	ADD	@X[$d0],@X[$c2],@X[$c2]
||	ADD	@X[$d1],@X[$c3],@X[$c3]
||	 XOR	@Y[$c2],@Y[$b0],@Y[$b0]
||	 XOR	@Y[$c3],@Y[$b1],@Y[$b1]
||	 XOR	@Y[$c0],@Y[$b2],@Y[$b2]
||	 XOR	@Y[$c1],@Y[$b3],@Y[$b3]
	ADD	@X[$d2],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c1],@X[$c1]
||	XOR	@X[$c2],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b1],@X[$b1]
||	ROTL	@X[$d0],0,@X[$d3]	; moved to avoid cross-path stall
||	ROTL	@X[$d1],0,@X[$d0]
	XOR	@X[$c0],@X[$b2],@X[$b2]
||	XOR	@X[$c1],@X[$b3],@X[$b3]
||	MV	@X[$d2],@X[$d1]
||	MV	@X[$d3],@X[$d2]
||	 ROTL	@Y[$b0],12,@Y[$b0]
||	 ROTL	@Y[$b1],12,@Y[$b1]
	ROTL	@X[$b0],7,@X[$b1]	; avoided cross-path stall
||	ROTL	@X[$b1],7,@X[$b2]
	ROTL	@X[$b2],7,@X[$b3]
||	ROTL	@X[$b3],7,@X[$b0]
|| [B0]	SUB	B0,1,B0			; decrement inner loop counter
bottom2x1?:

	 ROTL	@Y[$b2],12,@Y[$b2]
||	 ROTL	@Y[$b3],12,@Y[$b3]
|| [B0]	ADD	@X[$b1],@X[$a1],@X[$a1]	; modulo-scheduled
|| [B0]	ADD	@X[$b2],@X[$a2],@X[$a2]
   [B0]	ADD	@X[$b0],@X[$a0],@X[$a0]
|| [B0]	ADD	@X[$b3],@X[$a3],@X[$a3]

||	 ADD	@Y[$b0],@Y[$a0],@Y[$a0]
||	 ADD	@Y[$b1],@Y[$a1],@Y[$a1]
|| [B0]	XOR	@X[$a1],@X[$d1],@X[$d1]
|| [B0]	XOR	@X[$a2],@X[$d2],@X[$d2]
   [B0]	XOR	@X[$a0],@X[$d0],@X[$d0]
|| [B0]	XOR	@X[$a3],@X[$d3],@X[$d3]
||	 ADD	@Y[$b2],@Y[$a2],@Y[$a2]
||	 ADD	@Y[$b3],@Y[$a3],@Y[$a3]
||	 XOR	@Y[$a0],@Y[$d0],@Y[$d0]
||	 XOR	@Y[$a1],@Y[$d1],@Y[$d1]
	 XOR	@Y[$a2],@Y[$d2],@Y[$d2]
||	 XOR	@Y[$a3],@Y[$d3],@Y[$d3]
||	 ROTL	@Y[$d0],8,@Y[$d0]
||	 ROTL	@Y[$d1],8,@Y[$d1]
|| [B0]	SWAP2	@X[$d1],@X[$d1]		; rotate by 16
|| [B0]	SWAP2	@X[$d2],@X[$d2]
|| [B0]	SWAP2	@X[$d0],@X[$d0]
|| [B0]	SWAP2	@X[$d3],@X[$d3]
	 ROTL	@Y[$d2],8,@Y[$d2]
||	 ROTL	@Y[$d3],8,@Y[$d3]
|| [B0]	ADD	@X[$d1],@X[$c1],@X[$c1]
|| [B0]	ADD	@X[$d2],@X[$c2],@X[$c2]
|| [B0]	ADD	@X[$d0],@X[$c0],@X[$c0]
|| [B0]	ADD	@X[$d3],@X[$c3],@X[$c3]
|| [B0]	BNOP	top2x?			; even protects from interrupt

	 ADD	@Y[$d0],@Y[$c2],@Y[$c2]
||	 ADD	@Y[$d1],@Y[$c3],@Y[$c3]
|| [B0]	XOR	@X[$c1],@X[$b1],@X[$b1]
|| [B0]	XOR	@X[$c2],@X[$b2],@X[$b2]
|| [B0]	XOR	@X[$c0],@X[$b0],@X[$b0]
|| [B0]	XOR	@X[$c3],@X[$b3],@X[$b3]
	 ADD	@Y[$d2],@Y[$c0],@Y[$c0]
||	 ADD	@Y[$d3],@Y[$c1],@Y[$c1]
||	 XOR	@Y[$c2],@Y[$b0],@Y[$b0]
||	 XOR	@Y[$c3],@Y[$b1],@Y[$b1]
||	 ROTL	@Y[$d0],0,@Y[$d3]	; moved to avoid cross-path stall
||	 ROTL	@Y[$d1],0,@Y[$d0]
	 XOR	@Y[$c0],@Y[$b2],@Y[$b2]
||	 XOR	@Y[$c1],@Y[$b3],@Y[$b3]
||	 MV	@Y[$d2],@Y[$d1]
||	 MV	@Y[$d3],@Y[$d2]
|| [B0]	ROTL	@X[$b1],12,@X[$b1]
|| [B0]	ROTL	@X[$b2],12,@X[$b2]
	 ROTL	@Y[$b0],7,@Y[$b1]	; avoided cross-path stall
||	 ROTL	@Y[$b1],7,@Y[$b2]
	 ROTL	@Y[$b2],7,@Y[$b3]
||	 ROTL	@Y[$b3],7,@Y[$b0]
bottom2x2?:
___
}

$code.=<<___;
	ADD	@K2x[0],@X[0],@X[0]	; accumulate key material
||	ADD	@K2x[1],@X[1],@X[1]
||	ADD	@K2x[2],@X[2],@X[2]
||	ADD	@K2x[3],@X[3],@X[3]
	 ADD	@K2x[0],@Y[0],@Y[0]
||	 ADD	@K2x[1],@Y[1],@Y[1]
||	 ADD	@K2x[2],@Y[2],@Y[2]
||	 ADD	@K2x[3],@Y[3],@Y[3]
||	LDNDW	*${INP}++[8],@DAT[1]:@DAT[0]
	ADD	@K2x[4],@X[4],@X[4]
||	ADD	@K2x[5],@X[5],@X[5]
||	ADD	@K2x[6],@X[6],@X[6]
||	ADD	@K2x[7],@X[7],@X[7]
||	LDNDW	*${INP}[-7],@DAT[3]:@DAT[2]
	 ADD	@K2x[4],@Y[4],@Y[4]
||	 ADD	@K2x[5],@Y[5],@Y[5]
||	 ADD	@K2x[6],@Y[6],@Y[6]
||	 ADD	@K2x[7],@Y[7],@Y[7]
||	LDNDW	*${INP}[-6],@DAT[5]:@DAT[4]
	ADD	@K2x[8],@X[8],@X[8]
||	ADD	@K2x[9],@X[9],@X[9]
||	ADD	@K2x[10],@X[10],@X[10]
||	ADD	@K2x[11],@X[11],@X[11]
||	LDNDW	*${INP}[-5],@DAT[7]:@DAT[6]
	 ADD	@K2x[8],@Y[8],@Y[8]
||	 ADD	@K2x[9],@Y[9],@Y[9]
||	 ADD	@K2x[10],@Y[10],@Y[10]
||	 ADD	@K2x[11],@Y[11],@Y[11]
||	LDNDW	*${INP}[-4],@DAT[9]:@DAT[8]
	ADD	@K2x[12],@X[12],@X[12]
||	ADD	@K2x[13],@X[13],@X[13]
||	ADD	@K2x[14],@X[14],@X[14]
||	ADD	@K2x[15],@X[15],@X[15]
||	LDNDW	*${INP}[-3],@DAT[11]:@DAT[10]
	 ADD	@K2x[12],@Y[12],@Y[12]
||	 ADD	@K2x[13],@Y[13],@Y[13]
||	 ADD	@K2x[14],@Y[14],@Y[14]
||	 ADD	@K2x[15],@Y[15],@Y[15]
||	LDNDW	*${INP}[-2],@DAT[13]:@DAT[12]
	 ADD	1,@Y[12],@Y[12]		; adjust counter for 2nd block
||	ADD	2,@K2x[12],@K2x[12]	; increment counter
||	LDNDW	*${INP}[-1],@DAT[15]:@DAT[14]

	.if	.BIG_ENDIAN
	SWAP2	@X[0],@X[0]
||	SWAP2	@X[1],@X[1]
||	SWAP2	@X[2],@X[2]
||	SWAP2	@X[3],@X[3]
	SWAP2	@X[4],@X[4]
||	SWAP2	@X[5],@X[5]
||	SWAP2	@X[6],@X[6]
||	SWAP2	@X[7],@X[7]
	SWAP2	@X[8],@X[8]
||	SWAP2	@X[9],@X[9]
||	SWAP4	@X[0],@X[1]
||	SWAP4	@X[1],@X[0]
	SWAP2	@X[10],@X[10]
||	SWAP2	@X[11],@X[11]
||	SWAP4	@X[2],@X[3]
||	SWAP4	@X[3],@X[2]
	SWAP2	@X[12],@X[12]
||	SWAP2	@X[13],@X[13]
||	SWAP4	@X[4],@X[5]
||	SWAP4	@X[5],@X[4]
	SWAP2	@X[14],@X[14]
||	SWAP2	@X[15],@X[15]
||	SWAP4	@X[6],@X[7]
||	SWAP4	@X[7],@X[6]
	SWAP4	@X[8],@X[9]
||	SWAP4	@X[9],@X[8]
||	 SWAP2	@Y[0],@Y[0]
||	 SWAP2	@Y[1],@Y[1]
	SWAP4	@X[10],@X[11]
||	SWAP4	@X[11],@X[10]
||	 SWAP2	@Y[2],@Y[2]
||	 SWAP2	@Y[3],@Y[3]
	SWAP4	@X[12],@X[13]
||	SWAP4	@X[13],@X[12]
||	 SWAP2	@Y[4],@Y[4]
||	 SWAP2	@Y[5],@Y[5]
	SWAP4	@X[14],@X[15]
||	SWAP4	@X[15],@X[14]
||	 SWAP2	@Y[6],@Y[6]
||	 SWAP2	@Y[7],@Y[7]
	 SWAP2	@Y[8],@Y[8]
||	 SWAP2	@Y[9],@Y[9]
||	 SWAP4	@Y[0],@Y[1]
||	 SWAP4	@Y[1],@Y[0]
	 SWAP2	@Y[10],@Y[10]
||	 SWAP2	@Y[11],@Y[11]
||	 SWAP4	@Y[2],@Y[3]
||	 SWAP4	@Y[3],@Y[2]
	 SWAP2	@Y[12],@Y[12]
||	 SWAP2	@Y[13],@Y[13]
||	 SWAP4	@Y[4],@Y[5]
||	 SWAP4	@Y[5],@Y[4]
	 SWAP2	@Y[14],@Y[14]
||	 SWAP2	@Y[15],@Y[15]
||	 SWAP4	@Y[6],@Y[7]
||	 SWAP4	@Y[7],@Y[6]
	 SWAP4	@Y[8],@Y[9]
||	 SWAP4	@Y[9],@Y[8]
	 SWAP4	@Y[10],@Y[11]
||	 SWAP4	@Y[11],@Y[10]
	 SWAP4	@Y[12],@Y[13]
||	 SWAP4	@Y[13],@Y[12]
	 SWAP4	@Y[14],@Y[15]
||	 SWAP4	@Y[15],@Y[14]
	.endif

	XOR	@DAT[0],@X[0],@X[0]	; xor 1st block
||	XOR	@DAT[3],@X[3],@X[3]
||	XOR	@DAT[2],@X[2],@X[1]
||	XOR	@DAT[1],@X[1],@X[2]
||	LDNDW	*${INP}++[8],@DAT[1]:@DAT[0]
	XOR	@DAT[4],@X[4],@X[4]
||	XOR	@DAT[7],@X[7],@X[7]
||	LDNDW	*${INP}[-7],@DAT[3]:@DAT[2]
	XOR	@DAT[6],@X[6],@X[5]
||	XOR	@DAT[5],@X[5],@X[6]
||	LDNDW	*${INP}[-6],@DAT[5]:@DAT[4]
	XOR	@DAT[8],@X[8],@X[8]
||	XOR	@DAT[11],@X[11],@X[11]
||	LDNDW	*${INP}[-5],@DAT[7]:@DAT[6]
	XOR	@DAT[10],@X[10],@X[9]
||	XOR	@DAT[9],@X[9],@X[10]
||	LDNDW	*${INP}[-4],@DAT[9]:@DAT[8]
	XOR	@DAT[12],@X[12],@X[12]
||	XOR	@DAT[15],@X[15],@X[15]
||	LDNDW	*${INP}[-3],@DAT[11]:@DAT[10]
	XOR	@DAT[14],@X[14],@X[13]
||	XOR	@DAT[13],@X[13],@X[14]
||	LDNDW	*${INP}[-2],@DAT[13]:@DAT[12]
   [A0]	SUB	A0,$STEP,A0		; SUB	A0,128,A0
||	LDNDW	*${INP}[-1],@DAT[15]:@DAT[14]

	XOR	@Y[0],@DAT[0],@DAT[0]	; xor 2nd block
||	XOR	@Y[1],@DAT[1],@DAT[1]
||	STNDW	@X[2]:@X[0],*${OUT}++[8]
	XOR	@Y[2],@DAT[2],@DAT[2]
||	XOR	@Y[3],@DAT[3],@DAT[3]
||	STNDW	@X[3]:@X[1],*${OUT}[-7]
	XOR	@Y[4],@DAT[4],@DAT[4]
|| [A0]	LDDW	*FP[-12],@X[2]:@X[0]	; re-load key material from stack
|| [A0]	LDDW	*SP[2],  @X[3]:@X[1]
	XOR	@Y[5],@DAT[5],@DAT[5]
||	STNDW	@X[6]:@X[4],*${OUT}[-6]
	XOR	@Y[6],@DAT[6],@DAT[6]
||	XOR	@Y[7],@DAT[7],@DAT[7]
||	STNDW	@X[7]:@X[5],*${OUT}[-5]
	XOR	@Y[8],@DAT[8],@DAT[8]
|| [A0]	LDDW	*FP[-10],@X[6]:@X[4]
|| [A0]	LDDW	*SP[4],  @X[7]:@X[5]
	XOR	@Y[9],@DAT[9],@DAT[9]
||	STNDW	@X[10]:@X[8],*${OUT}[-4]
	XOR	@Y[10],@DAT[10],@DAT[10]
||	XOR	@Y[11],@DAT[11],@DAT[11]
||	STNDW	@X[11]:@X[9],*${OUT}[-3]
	XOR	@Y[12],@DAT[12],@DAT[12]
|| [A0]	LDDW	*FP[-8], @X[10]:@X[8]
|| [A0]	LDDW	*SP[6],  @X[11]:@X[9]
	XOR	@Y[13],@DAT[13],@DAT[13]
||	STNDW	@X[14]:@X[12],*${OUT}[-2]
	XOR	@Y[14],@DAT[14],@DAT[14]
||	XOR	@Y[15],@DAT[15],@DAT[15]
||	STNDW	@X[15]:@X[13],*${OUT}[-1]

   [A0]	MV	@K2x[12],@X[12]
|| [A0]	MV	@K2x[13],@X[13]
|| [A0]	LDW	*FP[-6*2], @X[14]
|| [A0]	LDW	*SP[8*2],  @X[15]

   [A0]	DMV	@X[2],@X[0],@Y[2]:@Y[0]	; duplicate key material
||	STNDW	@DAT[1]:@DAT[0],*${OUT}++[8]
   [A0]	DMV	@X[3],@X[1],@Y[3]:@Y[1]
||	STNDW	@DAT[3]:@DAT[2],*${OUT}[-7]
   [A0]	DMV	@X[6],@X[4],@Y[6]:@Y[4]
||	STNDW	@DAT[5]:@DAT[4],*${OUT}[-6]
||	CMPLTU	A0,$STEP,A1		; is remaining length < 2*blocks?
||[!A0]	BNOP	epilogue?
   [A0]	DMV	@X[7],@X[5],@Y[7]:@Y[5]
||	STNDW	@DAT[7]:@DAT[6],*${OUT}[-5]
||[!A1]	BNOP	outer2x?
   [A0]	DMV	@X[10],@X[8],@Y[10]:@Y[8]
||	STNDW	@DAT[9]:@DAT[8],*${OUT}[-4]
   [A0]	DMV	@X[11],@X[9],@Y[11]:@Y[9]
||	STNDW	@DAT[11]:@DAT[10],*${OUT}[-3]
   [A0]	DMV	@X[14],@X[12],@Y[14]:@Y[12]
||	STNDW	@DAT[13]:@DAT[12],*${OUT}[-2]
   [A0]	DMV	@X[15],@X[13],@Y[15]:@Y[13]
||	STNDW	@DAT[15]:@DAT[14],*${OUT}[-1]
;;===== branch to epilogue? is taken here
   [A1]	MVK	64,$STEP
|| [A0]	MVK	10,B0			; inner loop counter
;;===== branch to outer2x? is taken here
___
{
my ($a0,$a1,$a2,$a3) = (0..3);
my ($b0,$b1,$b2,$b3) = (4..7);
my ($c0,$c1,$c2,$c3) = (8..11);
my ($d0,$d1,$d2,$d3) = (12..15);

$code.=<<___;
top1x?:
	ADD	@X[$b1],@X[$a1],@X[$a1]
||	ADD	@X[$b2],@X[$a2],@X[$a2]
	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
||	XOR	@X[$a2],@X[$d2],@X[$d2]
	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	SWAP2	@X[$d1],@X[$d1]		; rotate by 16
||	SWAP2	@X[$d2],@X[$d2]
	SWAP2	@X[$d0],@X[$d0]
||	SWAP2	@X[$d3],@X[$d3]

||	ADD	@X[$d1],@X[$c1],@X[$c1]
||	ADD	@X[$d2],@X[$c2],@X[$c2]
	ADD	@X[$d0],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c3],@X[$c3]
||	XOR	@X[$c1],@X[$b1],@X[$b1]
||	XOR	@X[$c2],@X[$b2],@X[$b2]
	XOR	@X[$c0],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b3],@X[$b3]
||	ROTL	@X[$b1],12,@X[$b1]
||	ROTL	@X[$b2],12,@X[$b2]
	ROTL	@X[$b0],12,@X[$b0]
||	ROTL	@X[$b3],12,@X[$b3]

	ADD	@X[$b1],@X[$a1],@X[$a1]
||	ADD	@X[$b2],@X[$a2],@X[$a2]
	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
||	XOR	@X[$a2],@X[$d2],@X[$d2]
	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	ROTL	@X[$d1],8,@X[$d1]
||	ROTL	@X[$d2],8,@X[$d2]
	ROTL	@X[$d0],8,@X[$d0]
||	ROTL	@X[$d3],8,@X[$d3]
||	BNOP	middle1x?		; protect from interrupt

	ADD	@X[$d1],@X[$c1],@X[$c1]
||	ADD	@X[$d2],@X[$c2],@X[$c2]
	ADD	@X[$d0],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c3],@X[$c3]
||	XOR	@X[$c1],@X[$b1],@X[$b1]
||	XOR	@X[$c2],@X[$b2],@X[$b2]
||	ROTL	@X[$d1],0,@X[$d2]	; moved to avoid cross-path stall
||	ROTL	@X[$d2],0,@X[$d3]
	XOR	@X[$c0],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b3],@X[$b3]
||	ROTL	@X[$d0],0,@X[$d1]
||	ROTL	@X[$d3],0,@X[$d0]
	ROTL	@X[$b1],7,@X[$b0]	; avoided cross-path stall
||	ROTL	@X[$b2],7,@X[$b1]
	ROTL	@X[$b0],7,@X[$b3]
||	ROTL	@X[$b3],7,@X[$b2]
middle1x?:

	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b1],@X[$a1],@X[$a1]
	ADD	@X[$b2],@X[$a2],@X[$a2]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
	XOR	@X[$a2],@X[$d2],@X[$d2]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	SWAP2	@X[$d0],@X[$d0]		; rotate by 16
||	SWAP2	@X[$d1],@X[$d1]
	SWAP2	@X[$d2],@X[$d2]
||	SWAP2	@X[$d3],@X[$d3]

||	ADD	@X[$d0],@X[$c2],@X[$c2]
||	ADD	@X[$d1],@X[$c3],@X[$c3]
	ADD	@X[$d2],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c1],@X[$c1]
||	XOR	@X[$c2],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b1],@X[$b1]
	XOR	@X[$c0],@X[$b2],@X[$b2]
||	XOR	@X[$c1],@X[$b3],@X[$b3]
||	ROTL	@X[$b0],12,@X[$b0]
||	ROTL	@X[$b1],12,@X[$b1]
	ROTL	@X[$b2],12,@X[$b2]
||	ROTL	@X[$b3],12,@X[$b3]

	ADD	@X[$b0],@X[$a0],@X[$a0]
||	ADD	@X[$b1],@X[$a1],@X[$a1]
|| [B0]	SUB	B0,1,B0			; decrement inner loop counter
	ADD	@X[$b2],@X[$a2],@X[$a2]
||	ADD	@X[$b3],@X[$a3],@X[$a3]
||	XOR	@X[$a0],@X[$d0],@X[$d0]
||	XOR	@X[$a1],@X[$d1],@X[$d1]
	XOR	@X[$a2],@X[$d2],@X[$d2]
||	XOR	@X[$a3],@X[$d3],@X[$d3]
||	ROTL	@X[$d0],8,@X[$d0]
||	ROTL	@X[$d1],8,@X[$d1]
	ROTL	@X[$d2],8,@X[$d2]
||	ROTL	@X[$d3],8,@X[$d3]
|| [B0]	BNOP	top1x?			; even protects from interrupt

	ADD	@X[$d0],@X[$c2],@X[$c2]
||	ADD	@X[$d1],@X[$c3],@X[$c3]
	ADD	@X[$d2],@X[$c0],@X[$c0]
||	ADD	@X[$d3],@X[$c1],@X[$c1]
||	XOR	@X[$c2],@X[$b0],@X[$b0]
||	XOR	@X[$c3],@X[$b1],@X[$b1]
||	ROTL	@X[$d0],0,@X[$d3]	; moved to avoid cross-path stall
||	ROTL	@X[$d1],0,@X[$d0]
	XOR	@X[$c0],@X[$b2],@X[$b2]
||	XOR	@X[$c1],@X[$b3],@X[$b3]
||	ROTL	@X[$d2],0,@X[$d1]
||	ROTL	@X[$d3],0,@X[$d2]
	ROTL	@X[$b0],7,@X[$b1]	; avoided cross-path stall
||	ROTL	@X[$b1],7,@X[$b2]
	ROTL	@X[$b2],7,@X[$b3]
||	ROTL	@X[$b3],7,@X[$b0]
||[!B0]	CMPLTU	A0,$STEP,A1		; less than 64 bytes left?
bottom1x?:
___
}

$code.=<<___;
	ADD	@Y[0],@X[0],@X[0]	; accumulate key material
||	ADD	@Y[1],@X[1],@X[1]
||	ADD	@Y[2],@X[2],@X[2]
||	ADD	@Y[3],@X[3],@X[3]
||[!A1]	LDNDW	*${INP}++[8],@DAT[1]:@DAT[0]
|| [A1]	BNOP	tail?
	ADD	@Y[4],@X[4],@X[4]
||	ADD	@Y[5],@X[5],@X[5]
||	ADD	@Y[6],@X[6],@X[6]
||	ADD	@Y[7],@X[7],@X[7]
||[!A1]	LDNDW	*${INP}[-7],@DAT[3]:@DAT[2]
	ADD	@Y[8],@X[8],@X[8]
||	ADD	@Y[9],@X[9],@X[9]
||	ADD	@Y[10],@X[10],@X[10]
||	ADD	@Y[11],@X[11],@X[11]
||[!A1]	LDNDW	*${INP}[-6],@DAT[5]:@DAT[4]
	ADD	@Y[12],@X[12],@X[12]
||	ADD	@Y[13],@X[13],@X[13]
||	ADD	@Y[14],@X[14],@X[14]
||	ADD	@Y[15],@X[15],@X[15]
||[!A1]	LDNDW	*${INP}[-5],@DAT[7]:@DAT[6]
  [!A1]	LDNDW	*${INP}[-4],@DAT[9]:@DAT[8]
  [!A1]	LDNDW	*${INP}[-3],@DAT[11]:@DAT[10]
	LDNDW	*${INP}[-2],@DAT[13]:@DAT[12]
	LDNDW	*${INP}[-1],@DAT[15]:@DAT[14]

	.if	.BIG_ENDIAN
	SWAP2	@X[0],@X[0]
||	SWAP2	@X[1],@X[1]
||	SWAP2	@X[2],@X[2]
||	SWAP2	@X[3],@X[3]
	SWAP2	@X[4],@X[4]
||	SWAP2	@X[5],@X[5]
||	SWAP2	@X[6],@X[6]
||	SWAP2	@X[7],@X[7]
	SWAP2	@X[8],@X[8]
||	SWAP2	@X[9],@X[9]
||	SWAP4	@X[0],@X[1]
||	SWAP4	@X[1],@X[0]
	SWAP2	@X[10],@X[10]
||	SWAP2	@X[11],@X[11]
||	SWAP4	@X[2],@X[3]
||	SWAP4	@X[3],@X[2]
	SWAP2	@X[12],@X[12]
||	SWAP2	@X[13],@X[13]
||	SWAP4	@X[4],@X[5]
||	SWAP4	@X[5],@X[4]
	SWAP2	@X[14],@X[14]
||	SWAP2	@X[15],@X[15]
||	SWAP4	@X[6],@X[7]
||	SWAP4	@X[7],@X[6]
	SWAP4	@X[8],@X[9]
||	SWAP4	@X[9],@X[8]
	SWAP4	@X[10],@X[11]
||	SWAP4	@X[11],@X[10]
	SWAP4	@X[12],@X[13]
||	SWAP4	@X[13],@X[12]
	SWAP4	@X[14],@X[15]
||	SWAP4	@X[15],@X[14]
	.else
	NOP	1
	.endif

	XOR	@X[0],@DAT[0],@DAT[0]	; xor with input
||	XOR	@X[1],@DAT[1],@DAT[1]
||	XOR	@X[2],@DAT[2],@DAT[2]
||	XOR	@X[3],@DAT[3],@DAT[3]
|| [A0]	SUB	A0,$STEP,A0		; SUB	A0,64,A0
	XOR	@X[4],@DAT[4],@DAT[4]
||	XOR	@X[5],@DAT[5],@DAT[5]
||	XOR	@X[6],@DAT[6],@DAT[6]
||	XOR	@X[7],@DAT[7],@DAT[7]
||	STNDW	@DAT[1]:@DAT[0],*${OUT}++[8]
	XOR	@X[8],@DAT[8],@DAT[8]
||	XOR	@X[9],@DAT[9],@DAT[9]
||	XOR	@X[10],@DAT[10],@DAT[10]
||	XOR	@X[11],@DAT[11],@DAT[11]
||	STNDW	@DAT[3]:@DAT[2],*${OUT}[-7]
	XOR	@X[12],@DAT[12],@DAT[12]
||	XOR	@X[13],@DAT[13],@DAT[13]
||	XOR	@X[14],@DAT[14],@DAT[14]
||	XOR	@X[15],@DAT[15],@DAT[15]
||	STNDW	@DAT[5]:@DAT[4],*${OUT}[-6]
|| [A0]	BNOP	top1x?
   [A0]	DMV	@Y[2],@Y[0],@X[2]:@X[0]	; duplicate key material
|| [A0]	DMV	@Y[3],@Y[1],@X[3]:@X[1]
||	STNDW	@DAT[7]:@DAT[6],*${OUT}[-5]
   [A0]	DMV	@Y[6],@Y[4],@X[6]:@X[4]
|| [A0]	DMV	@Y[7],@Y[5],@X[7]:@X[5]
||	STNDW	@DAT[9]:@DAT[8],*${OUT}[-4]
   [A0]	DMV	@Y[10],@Y[8],@X[10]:@X[8]
|| [A0]	DMV	@Y[11],@Y[9],@X[11]:@X[9]
|| [A0]	ADD	1,@Y[12],@Y[12]		; increment counter
||	STNDW	@DAT[11]:@DAT[10],*${OUT}[-3]
   [A0]	DMV	@Y[14],@Y[12],@X[14]:@X[12]
|| [A0]	DMV	@Y[15],@Y[13],@X[15]:@X[13]
||	STNDW	@DAT[13]:@DAT[12],*${OUT}[-2]
   [A0]	MVK	10,B0			; inner loop counter
||	STNDW	@DAT[15]:@DAT[14],*${OUT}[-1]
;;===== branch to top1x? is taken here

epilogue?:
	LDDW	*FP[-4],A11:A10		; ABI says so
	LDDW	*FP[-3],A13:A12
||	LDDW	*SP[3+8],B11:B10
	LDDW	*SP[4+8],B13:B12
||	BNOP	RA
	LDW	*++SP(40+64),FP		; restore frame pointer
	NOP	4

tail?:
	LDBU	*${INP}++[1],B24	; load byte by byte
||	SUB	A0,1,A0
||	SUB	A0,1,B1
  [!B1]	BNOP	epilogue?		; interrupts are disabled for whole time
|| [A0] LDBU	*${INP}++[1],B24
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
  [!B1]	BNOP	epilogue?
|| [A0] LDBU	*${INP}++[1],B24
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
  [!B1]	BNOP	epilogue?
||	ROTL	@X[0],0,A24
|| [A0] LDBU	*${INP}++[1],B24
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
  [!B1]	BNOP	epilogue?
||	ROTL	@X[0],24,A24
|| [A0] LDBU	*${INP}++[1],A24
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
  [!B1]	BNOP	epilogue?
||	ROTL	@X[0],16,A24
|| [A0] LDBU	*${INP}++[1],A24
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
||	XOR	A24,B24,B25
	STB	B25,*${OUT}++[1]	; store byte by byte
||[!B1]	BNOP	epilogue?
||	ROTL	@X[0],8,A24
|| [A0] LDBU	*${INP}++[1],A24
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
||	XOR	A24,B24,B25
	STB	B25,*${OUT}++[1]
___
sub TAIL_STEP {
my $Xi= shift;
my $T = ($Xi=~/^B/?"B24":"A24");	# match @X[i] to avoid cross path
my $D = $T; $D=~tr/AB/BA/;
my $O = $D; $O=~s/24/25/;

$code.=<<___;
||[!B1]	BNOP	epilogue?
||	ROTL	$Xi,0,$T
|| [A0] LDBU	*${INP}++[1],$D
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
||	XOR	A24,B24,$O
	STB	$O,*${OUT}++[1]
||[!B1]	BNOP	epilogue?
||	ROTL	$Xi,24,$T
|| [A0] LDBU	*${INP}++[1],$T
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
||	XOR	A24,B24,$O
	STB	$O,*${OUT}++[1]
||[!B1]	BNOP	epilogue?
||	ROTL	$Xi,16,$T
|| [A0] LDBU	*${INP}++[1],$T
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
||	XOR	A24,B24,$O
	STB	$O,*${OUT}++[1]
||[!B1]	BNOP	epilogue?
||	ROTL	$Xi,8,$T
|| [A0] LDBU	*${INP}++[1],$T
|| [A0]	SUB	A0,1,A0
||	SUB	B1,1,B1
||	XOR	A24,B24,$O
	STB	$O,*${OUT}++[1]
___
}
	foreach (1..14) { TAIL_STEP(@X[$_]); }
$code.=<<___;
||[!B1]	BNOP	epilogue?
||	ROTL	@X[15],0,B24
||	XOR	A24,B24,A25
	STB	A25,*${OUT}++[1]
||	ROTL	@X[15],24,B24
||	XOR	A24,B24,A25
	STB	A25,*${OUT}++[1]
||	ROTL	@X[15],16,B24
||	XOR	A24,B24,A25
	STB	A25,*${OUT}++[1]
||	XOR	A24,B24,A25
	STB	A25,*${OUT}++[1]
||	XOR	A24,B24,B25
	STB	B25,*${OUT}++[1]
	.endasmfunc

	.sect	.const
	.cstring "ChaCha20 for C64x+, CRYPTOGAMS by <appro\@openssl.org>"
	.align	4
___

print $code;
close STDOUT or die "error closing STDOUT: $!";
