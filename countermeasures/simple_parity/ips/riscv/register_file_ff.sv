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
// Engineer:       Francesco Conti - f.conti@unibo.it                         //
//                                                                            //
// Design Name:    RISC-V register file                                       //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Register file with 31x 32 bit wide registers. Register 0   //
//                 is fixed to 0. This register file is based on flip-flops.  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_register_file
#(
    parameter ADDR_WIDTH    = 5,
    parameter DATA_WIDTH    = 32
)
(
    // Clock and Reset
    input  logic         clk,
    input  logic         rst_n,

    input  logic                   test_en_i,

    //Read port R1
    input  logic [ADDR_WIDTH-1:0]  raddr_a_i,
    output logic [DATA_WIDTH-1:0]  rdata_a_o,

    //Read port R2
    input  logic [ADDR_WIDTH-1:0]  raddr_b_i,
    output logic [DATA_WIDTH-1:0]  rdata_b_o,

    //Read port R3
    input  logic [ADDR_WIDTH-1:0]  raddr_c_i,
    output logic [DATA_WIDTH-1:0]  rdata_c_o,

    // Write port W1
    input logic [ADDR_WIDTH-1:0]   waddr_a_i,
    input logic [DATA_WIDTH-1:0]   wdata_a_i,
    input logic                    we_a_i,

    // Write port W2
    input logic [ADDR_WIDTH-1:0]   waddr_b_i,
    input logic [DATA_WIDTH-1:0]   wdata_b_i,
    input logic                    we_b_i
);

  localparam    NUM_WORDS = 2**ADDR_WIDTH;

  logic [NUM_WORDS-1:0][DATA_WIDTH-1:0] rf_reg;
  logic [NUM_WORDS-1:0]                 we_a_dec;
  logic [NUM_WORDS-1:0]                 we_b_dec;

  always_comb
  begin : we_a_decoder
    for (int i = 0; i < NUM_WORDS; i++) begin
      if (waddr_a_i == i)
        we_a_dec[i] = we_a_i;
      else
        we_a_dec[i] = 1'b0;
    end
  end

  always_comb
  begin : we_b_decoder
    for (int i=0; i<NUM_WORDS; i++) begin
      if (waddr_b_i == i)
        we_b_dec[i] = we_b_i;
      else
        we_b_dec[i] = 1'b0;
    end
  end

  genvar i;
  generate

    // loop from 1 to NUM_WORDS-1 as R0 is nil
    for (i = 1; i < NUM_WORDS; i++)
    begin : rf_gen

      always_ff @(posedge clk, negedge rst_n)
      begin : register_write_behavioral
        if (rst_n==1'b0) begin
          rf_reg[i] <= 'b0;
        end else begin
          if(we_b_dec[i] == 1'b1)
            rf_reg[i] <= wdata_b_i;
          else if(we_a_dec[i] == 1'b1)
            rf_reg[i] <= wdata_a_i;
        end
      end

    end

    // R0 is nil
    assign rf_reg[0] = '0;

  endgenerate

  assign rdata_a_o = rf_reg[raddr_a_i];
  assign rdata_b_o = rf_reg[raddr_b_i];
  assign rdata_c_o = rf_reg[raddr_c_i];
  
  // ---- DISPLAY REGISTERS
  logic[DATA_WIDTH-1:0] reg00_zero;
  logic[DATA_WIDTH-1:0] reg01_ra;
  logic[DATA_WIDTH-1:0] reg02_sp;
  logic[DATA_WIDTH-1:0] reg03_gp;
  logic[DATA_WIDTH-1:0] reg04_tp;
  logic[DATA_WIDTH-1:0] reg05_t0;
  logic[DATA_WIDTH-1:0] reg06_t1;
  logic[DATA_WIDTH-1:0] reg07_t2;
  logic[DATA_WIDTH-1:0] reg08_s0;
  logic[DATA_WIDTH-1:0] reg09_s1;
  logic[DATA_WIDTH-1:0] reg10_a0;
  logic[DATA_WIDTH-1:0] reg11_a1;
  logic[DATA_WIDTH-1:0] reg12_a2;
  logic[DATA_WIDTH-1:0] reg13_a3;
  logic[DATA_WIDTH-1:0] reg14_a4;
  logic[DATA_WIDTH-1:0] reg15_a5;
  logic[DATA_WIDTH-1:0] reg16_a6;
  logic[DATA_WIDTH-1:0] reg17_a7;
  logic[DATA_WIDTH-1:0] reg18_s2;
  logic[DATA_WIDTH-1:0] reg19_s3;
  logic[DATA_WIDTH-1:0] reg20_s4;
  logic[DATA_WIDTH-1:0] reg21_s5;
  logic[DATA_WIDTH-1:0] reg22_s6;
  logic[DATA_WIDTH-1:0] reg23_s7;
  logic[DATA_WIDTH-1:0] reg24_s8;
  logic[DATA_WIDTH-1:0] reg25_s9;
  logic[DATA_WIDTH-1:0] reg26_s10;
  logic[DATA_WIDTH-1:0] reg27_s11;
  logic[DATA_WIDTH-1:0] reg28_t3;
  logic[DATA_WIDTH-1:0] reg29_t4;
  logic[DATA_WIDTH-1:0] reg30_t5;
  logic[DATA_WIDTH-1:0] reg31_t6;
 
  assign reg00_zero  = rf_reg[0];
  assign reg01_ra    = rf_reg[1];
  assign reg02_sp    = rf_reg[2];
  assign reg03_gp    = rf_reg[3];
  assign reg04_tp    = rf_reg[4];
  assign reg05_t0    = rf_reg[5];
  assign reg06_t1    = rf_reg[6];
  assign reg07_t2    = rf_reg[7];
  assign reg08_s0    = rf_reg[8];
  assign reg09_s1    = rf_reg[9];
  assign reg10_a0    = rf_reg[10];
  assign reg11_a1    = rf_reg[11];
  assign reg12_a2    = rf_reg[12];
  assign reg13_a3    = rf_reg[13];
  assign reg14_a4    = rf_reg[14];
  assign reg15_a5    = rf_reg[15];
  assign reg16_a6    = rf_reg[16];
  assign reg17_a7    = rf_reg[17];
  assign reg18_s2    = rf_reg[18];
  assign reg19_s3    = rf_reg[19];
  assign reg20_s4    = rf_reg[20];
  assign reg21_s5    = rf_reg[21];
  assign reg22_s6    = rf_reg[22];
  assign reg23_s7    = rf_reg[23];
  assign reg24_s8    = rf_reg[24];
  assign reg25_s9    = rf_reg[25];
  assign reg26_s10   = rf_reg[26];
  assign reg27_s11   = rf_reg[27];
  assign reg28_t3    = rf_reg[28];
  assign reg29_t4    = rf_reg[29];
  assign reg30_t5    = rf_reg[30];
  assign reg31_t6    = rf_reg[31];

endmodule
