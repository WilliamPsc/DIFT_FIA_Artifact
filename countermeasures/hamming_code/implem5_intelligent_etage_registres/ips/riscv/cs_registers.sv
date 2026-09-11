// Copyright 2015 ETH Zurich and University of Bologna.
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the “License”); you may not use this file except in
// compliance with the License.  You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

////////////////////////////////////////////////////////////////////////////////
// Engineer:       Sven Stucki - svstucki@student.ethz.ch                     //
//                                                                            //
// Additional contributions by:                                               //
//                 Andreas Traber - atraber@iis.ee.ethz.ch                    //
//                                                                            //
// Design Name:    Control and Status Registers                               //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Control and Status Registers (CSRs) loosely following the  //
//                 RiscV draft priviledged instruction set spec (v1.7)        //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

`include "riscv_config.sv"

import riscv_defines::*;

`ifndef PULP_FPGA_EMUL
 `ifdef SYNTHESIS
  `define ASIC_SYNTHESIS
 `endif
`endif

module riscv_cs_registers
#(
  parameter N_HWLP       = 2,
  parameter N_HWLP_BITS  = $clog2(N_HWLP),
  parameter N_EXT_CNT    = 0
)
(
  // Clock and Reset
  input  logic        clk,
  input  logic        rst_n,

  // Core and Cluster ID
  input  logic  [3:0] core_id_i,
  input  logic  [5:0] cluster_id_i,

  // Interface to registers (SRAM like)
  input  logic        csr_access_i,
  input  logic [11:0] csr_addr_i,
  input  logic [31:0] csr_wdata_i,
  input  logic  [1:0] csr_op_i,
  output logic [31:0] csr_rdata_o,

  // Interrupts
  output logic        irq_enable_o,
  output logic [31:0] mepc_o,
`ifdef DIFT
  output logic [31:0] tpr_o_corr,
  output logic [31:0] tcr_o_corr,
`endif
  input  logic [31:0] pc_if_i,
  input  logic [31:0] pc_id_i,
  input  logic [31:0] pc_ex_i,
  input  logic        data_load_event_ex_i,
  input  logic        exc_save_if_i,
  input  logic        exc_save_id_i,
  input  logic        exc_restore_i,

  input  logic [5:0]  exc_cause_i,
  input  logic        save_exc_cause_i,

  // Hardware loops
  input  logic [N_HWLP-1:0] [31:0] hwlp_start_i,
  input  logic [N_HWLP-1:0] [31:0] hwlp_end_i,
  input  logic [N_HWLP-1:0] [31:0] hwlp_cnt_i,

  output logic [31:0]              hwlp_data_o,
  output logic [N_HWLP_BITS-1:0]   hwlp_regid_o,
  output logic [2:0]               hwlp_we_o,

  // Performance Counters
  input  logic                 id_valid_i,        // ID stage is done
  input  logic                 is_compressed_i,   // compressed instruction in ID
  input  logic                 is_decoding_i,     // controller is in DECODE state

  input  logic                 imiss_i,           // instruction fetch
  input  logic                 pc_set_i,          // pc was set to a new value
  input  logic                 jump_i,            // jump instruction seen   (j, jr, jal, jalr)
  input  logic                 branch_i,          // branch instruction seen (bf, bnf)
  input  logic                 branch_taken_i,    // branch was taken
  input  logic                 ld_stall_i,        // load use hazard
  input  logic                 jr_stall_i,        // jump register use hazard

  input  logic                 mem_load_i,        // load from memory in this cycle
  input  logic                 mem_store_i,       // store to memory in this cycle

  input  logic [N_EXT_CNT-1:0] ext_counters_i
);

  localparam N_PERF_COUNTERS = 11 + N_EXT_CNT;

`ifdef ASIC_SYNTHESIS
  localparam N_PERF_REGS     = 1;
`else
  localparam N_PERF_REGS     = N_PERF_COUNTERS;
`endif

  // Performance Counter Signals
  logic                          id_valid_q;
  logic [N_PERF_COUNTERS-1:0]    PCCR_in;  // input signals for each counter category
  logic [N_PERF_COUNTERS-1:0]    PCCR_inc, PCCR_inc_q; // should the counter be increased?

  logic [N_PERF_REGS-1:0] [31:0] PCCR_q, PCCR_n; // performance counters counter register
  logic [1:0]                    PCMR_n, PCMR_q; // mode register, controls saturation and global enable
  logic [N_PERF_COUNTERS-1:0]    PCER_n, PCER_q; // selected counter input

  logic [31:0]                   perf_rdata;
  logic [4:0]                    pccr_index;
  logic                          pccr_all_sel;
  logic                          is_pccr;
  logic                          is_pcer;
  logic                          is_pcmr;

  // CSR update logic
  logic [31:0] csr_wdata_int;
  logic [31:0] csr_rdata_int;
  logic        csr_we_int;

  // Interrupt control signals
  logic [31:0] mepc_q, mepc_n;
  logic [ 0:0] mestatus_q, mestatus_n;
  logic [ 0:0] mstatus_q, mstatus_n;
  logic [ 5:0] exc_cause, exc_cause_n;

`ifdef DIFT
  logic [31:0] tpr_q, tpr_n;
  logic [31:0] tcr_q, tcr_n;
  logic        sec_interrupt;

  logic [1:0]  group0_corr;
  logic [2:0]  group0_hc;
  logic        sec_interrupt_0;

  logic [1:0]  group1_corr;
  logic [2:0]  group1_hc;
  logic        sec_interrupt_1;

  logic [1:0]  group2_corr;
  logic [2:0]  group2_hc;
  logic        sec_interrupt_2;

  logic [1:0]  group3_corr;
  logic [2:0]  group3_hc;
  logic        sec_interrupt_3;

  logic [1:0]  group4_corr;
  logic [2:0]  group4_hc;
  logic        sec_interrupt_4;

  logic [1:0]  group5_corr;
  logic [2:0]  group5_hc;
  logic        sec_interrupt_5;

  logic [1:0]  group6_corr;
  logic [2:0]  group6_hc;
  logic        sec_interrupt_6;

  logic [1:0]  group7_corr;
  logic [2:0]  group7_hc;
  logic        sec_interrupt_7;

  logic [1:0]  group8_corr;
  logic [2:0]  group8_hc;
  logic        sec_interrupt_8;

  logic [1:0]  group9_corr;
  logic [2:0]  group9_hc;
  logic        sec_interrupt_9;

  logic [1:0]  group10_corr;
  logic [2:0]  group10_hc;
  logic        sec_interrupt_10;

  logic [1:0]  group11_corr;
  logic [2:0]  group11_hc;
  logic        sec_interrupt_11;

  logic [1:0]  group12_corr;
  logic [2:0]  group12_hc;
  logic        sec_interrupt_12;

  logic [1:0]  group13_corr;
  logic [2:0]  group13_hc;
  logic        sec_interrupt_13;

  logic        group14_corr;
  logic [1:0]  group14_hc;
  logic        sec_interrupt_14;

  logic [1:0]  group15_corr;
  logic [2:0]  group15_hc;
  logic        sec_interrupt_15;

  logic [1:0]  group16_corr;
  logic [2:0]  group16_hc;
  logic        sec_interrupt_16;

  logic [1:0]  group17_corr;
  logic [2:0]  group17_hc;
  logic        sec_interrupt_17;

  logic        group18_corr;
  logic [1:0]  group18_hc;
  logic        sec_interrupt_18;

  logic        group19_corr;
  logic [1:0]  group19_hc;
  logic        sec_interrupt_19;

  logic        group20_corr;
  logic [1:0]  group20_hc;
  logic        sec_interrupt_20;

  logic        group21_corr;
  logic [1:0]  group21_hc;
  logic        sec_interrupt_21;
`endif

  ////////////////////////////////////////////
  //   ____ ____  ____    ____              //
  //  / ___/ ___||  _ \  |  _ \ ___  __ _   //
  // | |   \___ \| |_) | | |_) / _ \/ _` |  //
  // | |___ ___) |  _ <  |  _ <  __/ (_| |  //
  //  \____|____/|_| \_\ |_| \_\___|\__, |  //
  //                                |___/   //
  ////////////////////////////////////////////

  // read logic
  always_comb
  begin
    csr_rdata_int = 'x;

    case (csr_addr_i)
      // mstatus: always M-mode, contains IE bit
      12'h300: csr_rdata_int = {29'b0, 2'b11, mstatus_q};

      // mepc: exception program counter
      12'h341: csr_rdata_int = mepc_q;
      // mcause: exception cause
      12'h342: csr_rdata_int = {exc_cause[5], 26'b0, exc_cause[4:0]};

      // mcpuid: RV32IM and X
      12'hF00: csr_rdata_int = 32'h00_80_11_00;
      // mimpid: PULP, anonymous source (no allocated ID yet)
      12'hF01: csr_rdata_int = 32'h00_00_80_00;
      // mhartid: unique hardware thread id
      12'hF10: csr_rdata_int = {21'b0, cluster_id_i[5:0], 1'b0, core_id_i[3:0]};

      // hardware loops
      12'h7B0: csr_rdata_int = hwlp_start_i[0];
      12'h7B1: csr_rdata_int = hwlp_end_i[0];
      12'h7B2: csr_rdata_int = hwlp_cnt_i[0];
      12'h7B4: csr_rdata_int = hwlp_start_i[1];
      12'h7B5: csr_rdata_int = hwlp_end_i[1];
      12'h7B6: csr_rdata_int = hwlp_cnt_i[1];

    `ifdef DIFT
      12'h700: csr_rdata_int = tpr_o_corr;
      12'h701: csr_rdata_int = tcr_o_corr;
    `endif

      12'h7C0: csr_rdata_int = {29'b0, 2'b11, mestatus_q};
    endcase
  end

  `ifdef DIFT
    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group0 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[0], tpr_n[0]}  ),
      .hc_o         ( group0_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group0 (
      .hc_i           ( group0_hc             ),
      .reg_i          ( {tcr_q[0], tpr_q[0]}  ),
      .reg_o_corr     ( group0_corr           ),
      .sec_interrupt  ( sec_interrupt_0       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group1 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[1], tpr_n[1]}  ),
      .hc_o         ( group1_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group1 (
      .hc_i           ( group1_hc             ),
      .reg_i          ( {tcr_q[1], tpr_q[1]}  ),
      .reg_o_corr     ( group1_corr           ),
      .sec_interrupt  ( sec_interrupt_1       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group2 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[2], tpr_n[2]}  ),
      .hc_o         ( group2_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group2 (
      .hc_i           ( group2_hc             ),
      .reg_i          ( {tcr_q[2], tpr_q[2]}  ),
      .reg_o_corr     ( group2_corr           ),
      .sec_interrupt  ( sec_interrupt_2       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group3 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[3], tpr_n[3]}  ),
      .hc_o         ( group3_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group3 (
      .hc_i           ( group3_hc             ),
      .reg_i          ( {tcr_q[3], tpr_q[3]}  ),
      .reg_o_corr     ( group3_corr           ),
      .sec_interrupt  ( sec_interrupt_3       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group4 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[4], tpr_n[4]}  ),
      .hc_o         ( group4_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group4 (
      .hc_i           ( group4_hc             ),
      .reg_i          ( {tcr_q[4], tpr_q[4]}  ),
      .reg_o_corr     ( group4_corr           ),
      .sec_interrupt  ( sec_interrupt_4       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group5 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[5], tpr_n[5]}  ),
      .hc_o         ( group5_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group5 (
      .hc_i           ( group5_hc             ),
      .reg_i          ( {tcr_q[5], tpr_q[5]}  ),
      .reg_o_corr     ( group5_corr           ),
      .sec_interrupt  ( sec_interrupt_5       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group6 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[6], tpr_n[6]}  ),
      .hc_o         ( group6_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group6 (
      .hc_i           ( group6_hc             ),
      .reg_i          ( {tcr_q[6], tpr_q[6]}  ),
      .reg_o_corr     ( group6_corr           ),
      .sec_interrupt  ( sec_interrupt_6       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group7 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[7], tpr_n[7]}  ),
      .hc_o         ( group7_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group7 (
      .hc_i           ( group7_hc             ),
      .reg_i          ( {tcr_q[7], tpr_q[7]}  ),
      .reg_o_corr     ( group7_corr           ),
      .sec_interrupt  ( sec_interrupt_7       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group8 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[8], tpr_n[8]}  ),
      .hc_o         ( group8_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group8 (
      .hc_i           ( group8_hc             ),
      .reg_i          ( {tcr_q[8], tpr_q[8]}  ),
      .reg_o_corr     ( group8_corr           ),
      .sec_interrupt  ( sec_interrupt_8       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group9 (
      .clk          ( clk                   ),
      .reg_i        ( {tcr_n[9], tpr_n[9]}  ),
      .hc_o         ( group9_hc             )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group9 (
      .hc_i           ( group9_hc             ),
      .reg_i          ( {tcr_q[9], tpr_q[9]}  ),
      .reg_o_corr     ( group9_corr           ),
      .sec_interrupt  ( sec_interrupt_9       )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group10 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[10], tpr_n[10]}  ),
      .hc_o         ( group10_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group10 (
      .hc_i           ( group10_hc              ),
      .reg_i          ( {tcr_q[10], tpr_q[10]}  ),
      .reg_o_corr     ( group10_corr            ),
      .sec_interrupt  ( sec_interrupt_10        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group11 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[11], tpr_n[11]}  ),
      .hc_o         ( group11_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group11 (
      .hc_i           ( group11_hc              ),
      .reg_i          ( {tcr_q[11], tpr_q[11]}  ),
      .reg_o_corr     ( group11_corr            ),
      .sec_interrupt  ( sec_interrupt_11        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group12 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[12], tpr_n[12]}  ),
      .hc_o         ( group12_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group12 (
      .hc_i           ( group12_hc              ),
      .reg_i          ( {tcr_q[12], tpr_q[12]}  ),
      .reg_o_corr     ( group12_corr            ),
      .sec_interrupt  ( sec_interrupt_12        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group13 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[13], tpr_n[13]}  ),
      .hc_o         ( group13_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group13 (
      .hc_i           ( group13_hc              ),
      .reg_i          ( {tcr_q[13], tpr_q[13]}  ),
      .reg_o_corr     ( group13_corr            ),
      .sec_interrupt  ( sec_interrupt_13        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_encoder_csr_group14 (
      .clk          ( clk         ),
      .reg_i        ( tcr_n[14]   ),
      .hc_o         ( group14_hc  )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_decoder_csr_group14 (
      .hc_i           ( group14_hc        ),
      .reg_i          ( tcr_q[14]         ),
      .reg_o_corr     ( group14_corr      ),
      .sec_interrupt  ( sec_interrupt_14  )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group15 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[15], tpr_n[15]}  ),
      .hc_o         ( group15_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group15 (
      .hc_i           ( group15_hc              ),
      .reg_i          ( {tcr_q[15], tpr_q[15]}  ),
      .reg_o_corr     ( group15_corr            ),
      .sec_interrupt  ( sec_interrupt_15        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group16 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[16], tpr_n[16]}  ),
      .hc_o         ( group16_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group16 (
      .hc_i           ( group16_hc              ),
      .reg_i          ( {tcr_q[16], tpr_q[16]}  ),
      .reg_o_corr     ( group16_corr            ),
      .sec_interrupt  ( sec_interrupt_16        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_encoder_csr_group17 (
      .clk          ( clk                     ),
      .reg_i        ( {tcr_n[17], tpr_n[17]}  ),
      .hc_o         ( group17_hc              )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(2), .HC_SIZE(3)) hamming_code_decoder_csr_group17 (
      .hc_i           ( group17_hc              ),
      .reg_i          ( {tcr_q[17], tpr_q[17]}  ),
      .reg_o_corr     ( group17_corr            ),
      .sec_interrupt  ( sec_interrupt_17        )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_encoder_csr_group18 (
      .clk          ( clk           ),
      .reg_i        ( tcr_n[18]     ),
      .hc_o         ( group18_hc    )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_decoder_csr_group18 (
      .hc_i           ( group18_hc        ),
      .reg_i          ( tcr_q[18]         ),
      .reg_o_corr     ( group18_corr      ),
      .sec_interrupt  ( sec_interrupt_18  )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_encoder_csr_group19 (
      .clk          ( clk         ),
      .reg_i        ( tcr_n[19]   ),
      .hc_o         ( group19_hc  )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_decoder_csr_group19 (
      .hc_i           ( group19_hc        ),
      .reg_i          ( tcr_q[19]         ),
      .reg_o_corr     ( group19_corr      ),
      .sec_interrupt  ( sec_interrupt_19  )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_encoder_csr_group20 (
      .clk          ( clk         ),
      .reg_i        ( tcr_n[20]   ),
      .hc_o         ( group20_hc  )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_decoder_csr_group20 (
      .hc_i           ( group20_hc        ),
      .reg_i          ( tcr_q[20]         ),
      .reg_o_corr     ( group20_corr      ),
      .sec_interrupt  ( sec_interrupt_20  )
    );

    // -----------------------------------------------------------------------------------------------
    riscv_hamming_code_encoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_encoder_csr_group21 (
      .clk          ( clk         ),
      .reg_i        ( tcr_n[21]   ),
      .hc_o         ( group21_hc  )
    );

    riscv_hamming_code_decoder #(.REG_SIZE(1), .HC_SIZE(2)) hamming_code_decoder_csr_group21 (
      .hc_i           ( group21_hc        ),
      .reg_i          ( tcr_q[21]         ),
      .reg_o_corr     ( group21_corr      ),
      .sec_interrupt  ( sec_interrupt_21  )
    );

    // -----------------------------------------------------------------------------------------------
    assign tpr_o_corr = {group17_corr[0], group16_corr[0], group15_corr[0], 1'b0, group13_corr[0], group12_corr[0], group11_corr[0], group10_corr[0], group9_corr[0], group8_corr[0], group7_corr[0], group6_corr[0], group5_corr[0], group4_corr[0], group3_corr[0], group2_corr[0], group1_corr[0], group0_corr[0]};
    // -----------------------------------------------------------------------------------------------
    assign tcr_o_corr = {group21_corr, group20_corr, group19_corr, group18_corr, group17_corr[1], group16_corr[1], group15_corr[1], group14_corr, group13_corr[1], group12_corr[1], group11_corr[1], group10_corr[1], group9_corr[1], group8_corr[1], group7_corr[1], group6_corr[1], group5_corr[1], group4_corr[1], group3_corr[1], group2_corr[1], group1_corr[1], group0_corr[1]};
    // -----------------------------------------------------------------------------------------------
    assign sec_interrupt = sec_interrupt_0 | sec_interrupt_1 | sec_interrupt_2 | sec_interrupt_3 | sec_interrupt_4 | sec_interrupt_5 | sec_interrupt_6 | sec_interrupt_7 | sec_interrupt_8 | sec_interrupt_9 | sec_interrupt_10 | sec_interrupt_11 | sec_interrupt_12 | sec_interrupt_13 | sec_interrupt_14 | sec_interrupt_15 | sec_interrupt_16 | sec_interrupt_17 | sec_interrupt_18 | sec_interrupt_19 | sec_interrupt_20 | sec_interrupt_21;
  `endif

  // write logic
  always_comb
  begin
    mepc_n       = mepc_q;
    mestatus_n   = mestatus_q;
    mstatus_n    = mstatus_q;
    exc_cause_n  = exc_cause;
    hwlp_we_o    = '0;
    hwlp_regid_o = '0;

  `ifdef DIFT
    tpr_n = tpr_o_corr;
    tcr_n = tcr_o_corr;
  `endif

    case (csr_addr_i)
      // mstatus: IE bit
      12'h300: if (csr_we_int) mstatus_n = csr_wdata_int[0];

      // mepc: exception program counter
      12'h341: if (csr_we_int) mepc_n = csr_wdata_int;
      // mcause
      12'h342: if (csr_we_int) exc_cause_n = {csr_wdata_int[5], csr_wdata_int[4:0]};

      // hardware loops
      12'h7B0: if (csr_we_int) begin hwlp_we_o = 3'b001; hwlp_regid_o = 1'b0; end
      12'h7B1: if (csr_we_int) begin hwlp_we_o = 3'b010; hwlp_regid_o = 1'b0; end
      12'h7B2: if (csr_we_int) begin hwlp_we_o = 3'b100; hwlp_regid_o = 1'b0; end
      12'h7B4: if (csr_we_int) begin hwlp_we_o = 3'b001; hwlp_regid_o = 1'b1; end
      12'h7B5: if (csr_we_int) begin hwlp_we_o = 3'b010; hwlp_regid_o = 1'b1; end
      12'h7B6: if (csr_we_int) begin hwlp_we_o = 3'b100; hwlp_regid_o = 1'b1; end

    `ifdef DIFT
      12'h700: if (csr_we_int) tpr_n = csr_wdata_int;
      12'h701: if (csr_we_int) tcr_n = csr_wdata_int;
    `endif

      // mestatus: machine exception status
      12'h7C0: if (csr_we_int) mestatus_n = csr_wdata_int[0];
    endcase

    // exception controller gets priority over other writes
    if (exc_save_if_i || exc_save_id_i) begin
      mestatus_n = mstatus_q;
      mstatus_n  = 1'b0;

      if (data_load_event_ex_i) begin
        mepc_n = pc_ex_i;
      end else begin
        if (exc_save_if_i)
          mepc_n = pc_if_i;
        else
          mepc_n = pc_id_i;
      end
    end

    if (save_exc_cause_i)
      exc_cause_n = exc_cause_i;

    if (exc_restore_i) begin
      mstatus_n = mestatus_q;
    end
  end

  assign hwlp_data_o = csr_wdata_int;

  // CSR operation logic
  always_comb
  begin
    csr_wdata_int = csr_wdata_i;
    csr_we_int    = 1'b1;

    unique case (csr_op_i)
      CSR_OP_WRITE: csr_wdata_int = csr_wdata_i;
      CSR_OP_SET:   csr_wdata_int = csr_wdata_i | csr_rdata_o;
      CSR_OP_CLEAR: csr_wdata_int = (~csr_wdata_i) & csr_rdata_o;

      CSR_OP_NONE: begin
        csr_wdata_int = csr_wdata_i;
        csr_we_int    = 1'b0;
      end

      default:;
    endcase
  end

  // output mux
  always_comb
  begin
    csr_rdata_o = csr_rdata_int;

    // performance counters
    if (is_pccr || is_pcer || is_pcmr)
      csr_rdata_o = perf_rdata;
  end

  assign csr_we_int_o = csr_we_int;

  // directly output some registers
  assign irq_enable_o = mstatus_q[0];
  assign mepc_o       = mepc_q;

  // actual registers
  always_ff @(posedge clk, negedge rst_n)
  begin
    if (rst_n == 1'b0)
    begin
      mstatus_q  <= '0;
      mepc_q     <= '0;
      mestatus_q <= '0;
      exc_cause  <= '0;

    `ifdef DIFT
    	// DEFAULT
      tpr_q = 32'b00000000000000001010100010100010;
      tcr_q = 32'b00000000001101000001100000000000;
    `endif
    end
    else
    begin
      // update CSRs
      mstatus_q  <= mstatus_n;
      mepc_q     <= mepc_n;
      mestatus_q <= mestatus_n;
      exc_cause  <= exc_cause_n;

    `ifdef DIFT
      tpr_q = tpr_n;
      tcr_q = tcr_n;
    `endif
    end
  end

  /////////////////////////////////////////////////////////////////
  //   ____            __     ____                  _            //
  // |  _ \ ___ _ __ / _|   / ___|___  _   _ _ __ | |_ ___ _ __  //
  // | |_) / _ \ '__| |_   | |   / _ \| | | | '_ \| __/ _ \ '__| //
  // |  __/  __/ |  |  _|  | |__| (_) | |_| | | | | ||  __/ |    //
  // |_|   \___|_|  |_|(_)  \____\___/ \__,_|_| |_|\__\___|_|    //
  //                                                             //
  /////////////////////////////////////////////////////////////////

  assign PCCR_in[0]  = 1'b1;                          // cycle counter
  assign PCCR_in[1]  = id_valid_i & is_decoding_i;    // instruction counter
  assign PCCR_in[2]  = ld_stall_i & id_valid_q;       // nr of load use hazards
  assign PCCR_in[3]  = jr_stall_i & id_valid_q;       // nr of jump register hazards
  assign PCCR_in[4]  = imiss_i & (~pc_set_i);         // cycles waiting for instruction fetches, excluding jumps and branches
  assign PCCR_in[5]  = mem_load_i;                    // nr of loads
  assign PCCR_in[6]  = mem_store_i;                   // nr of stores
  assign PCCR_in[7]  = jump_i                     & id_valid_q; // nr of jumps (unconditional)
  assign PCCR_in[8]  = branch_i                   & id_valid_q; // nr of branches (conditional)
  assign PCCR_in[9]  = branch_i & branch_taken_i  & id_valid_q; // nr of taken branches (conditional)
  assign PCCR_in[10] = id_valid_i & is_decoding_i & is_compressed_i;  // compressed instruction counter

  // assign external performance counters
  generate
    genvar i;
    for(i = 0; i < N_EXT_CNT; i++)
    begin
      assign PCCR_in[N_PERF_COUNTERS - N_EXT_CNT + i] = ext_counters_i[i];
    end
  endgenerate

  // address decoder for performance counter registers
  always_comb
  begin
    is_pccr      = 1'b0;
    is_pcmr      = 1'b0;
    is_pcer      = 1'b0;
    pccr_all_sel = 1'b0;
    pccr_index   = '0;
    perf_rdata   = '0;

    // only perform csr access if we actually care about the read data
    if (csr_access_i) begin
      unique case (csr_addr_i)
        12'h7A0: begin
          is_pcer = 1'b1;
          perf_rdata[N_PERF_COUNTERS-1:0] = PCER_q;
        end
        12'h7A1: begin
          is_pcmr = 1'b1;
          perf_rdata[1:0] = PCMR_q;
        end
        12'h79F: begin
          is_pccr = 1'b1;
          pccr_all_sel = 1'b1;
        end
        default:;
      endcase

      // look for 780 to 79F, Performance Counter Counter Registers
      if (csr_addr_i[11:5] == 7'b0111100) begin
        is_pccr     = 1'b1;

        pccr_index = csr_addr_i[4:0];
`ifdef  ASIC_SYNTHESIS
        perf_rdata = PCCR_q[0];
`else
        perf_rdata = PCCR_q[csr_addr_i[4:0]];
`endif
      end
    end
  end


  // performance counter counter update logic
`ifdef ASIC_SYNTHESIS
  // for synthesis we just have one performance counter register
  assign PCCR_inc[0] = (|(PCCR_in & PCER_q)) & PCMR_q[0];

  always_comb
  begin
    PCCR_n[0]   = PCCR_q[0];

    if ((PCCR_inc_q[0] == 1'b1) && ((PCCR_q[0] != 32'hFFFFFFFF) || (PCMR_q[1] == 1'b0)))
      PCCR_n[0] = PCCR_q[0] + 1;

    if (is_pccr == 1'b1) begin
      unique case (csr_op_i)
        CSR_OP_NONE:   ;
        CSR_OP_WRITE:  PCCR_n[0] = csr_wdata_i;
        CSR_OP_SET:    PCCR_n[0] = csr_wdata_i | PCCR_q[0];
        CSR_OP_CLEAR:  PCCR_n[0] = csr_wdata_i & ~(PCCR_q[0]);
      endcase
    end
  end
`else
  always_comb
  begin
    for(int i = 0; i < N_PERF_COUNTERS; i++)
    begin : PERF_CNT_INC
      PCCR_inc[i] = PCCR_in[i] & PCER_q[i] & PCMR_q[0];

      PCCR_n[i]   = PCCR_q[i];

      if ((PCCR_inc_q[i] == 1'b1) && ((PCCR_q[i] != 32'hFFFFFFFF) || (PCMR_q[1] == 1'b0)))
        PCCR_n[i] = PCCR_q[i] + 1;

      if (is_pccr == 1'b1 && (pccr_all_sel == 1'b1 || pccr_index == i)) begin
        unique case (csr_op_i)
          CSR_OP_NONE:   ;
          CSR_OP_WRITE:  PCCR_n[i] = csr_wdata_i;
          CSR_OP_SET:    PCCR_n[i] = csr_wdata_i | PCCR_q[i];
          CSR_OP_CLEAR:  PCCR_n[i] = csr_wdata_i & ~(PCCR_q[i]);
        endcase
      end
    end
  end
`endif

  // update PCMR and PCER
  always_comb
  begin
    PCMR_n = PCMR_q;
    PCER_n = PCER_q;

    if (is_pcmr) begin
      unique case (csr_op_i)
        CSR_OP_NONE:   ;
        CSR_OP_WRITE:  PCMR_n = csr_wdata_i[1:0];
        CSR_OP_SET:    PCMR_n = csr_wdata_i[1:0] | PCMR_q;
        CSR_OP_CLEAR:  PCMR_n = csr_wdata_i[1:0] & ~(PCMR_q);
      endcase
    end

    if (is_pcer) begin
      unique case (csr_op_i)
        CSR_OP_NONE:   ;
        CSR_OP_WRITE:  PCER_n = csr_wdata_i[N_PERF_COUNTERS-1:0];
        CSR_OP_SET:    PCER_n = csr_wdata_i[N_PERF_COUNTERS-1:0] | PCER_q;
        CSR_OP_CLEAR:  PCER_n = csr_wdata_i[N_PERF_COUNTERS-1:0] & ~(PCER_q);
      endcase
    end
  end

  // Performance Counter Registers
  always_ff @(posedge clk, negedge rst_n)
  begin
    if (rst_n == 1'b0)
    begin
      id_valid_q <= 1'b0;

      PCER_q <= '0;
      PCMR_q <= 2'h3;

      for(int i = 0; i < N_PERF_REGS; i++)
      begin
        PCCR_q[i]     <= '0;
        PCCR_inc_q[i] <= '0;
      end
    end
    else
    begin
      id_valid_q <= id_valid_i;

      PCER_q <= PCER_n;
      PCMR_q <= PCMR_n;

      for(int i = 0; i < N_PERF_REGS; i++)
      begin
        PCCR_q[i]     <= PCCR_n[i];
        PCCR_inc_q[i] <= PCCR_inc[i];
      end

    end
  end

endmodule
