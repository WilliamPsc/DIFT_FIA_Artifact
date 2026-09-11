////////////////////////////////////////////////////////////////////////////////
// Engineer:       Christian Palmiero - cp3025@columbia.edu                   //
//                                                                            //
//                                                                            //
// Design Name:    RISC-V register file tag                                   //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Register file with 31x1 bit tags. Tag 0                    //
//                 is fixed to 0. This register file is based on flip-flops   //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_register_file_tag #(
    parameter ADDR_WIDTH = 5,
    parameter DATA_WIDTH = 1
) (
    // Clock and Reset
    input logic clk,
    input logic rst_n,

    input logic test_en_i,

    //Read port R1
    input  logic [ADDR_WIDTH-1:0] raddr_a_i,
    output logic [DATA_WIDTH-1:0] rdata_a_o,

    //Read port R2
    input  logic [ADDR_WIDTH-1:0] raddr_b_i,
    output logic [DATA_WIDTH-1:0] rdata_b_o,

    //Read port R3
    input  logic [ADDR_WIDTH-1:0] raddr_c_i,
    output logic [DATA_WIDTH-1:0] rdata_c_o,

    // Write port W1
    input logic [ADDR_WIDTH-1:0] waddr_a_i,
    input logic [DATA_WIDTH-1:0] wdata_a_i,
    input logic                  we_a_i,

    // Write port W2
    input logic [ADDR_WIDTH-1:0]   waddr_b_i,
    input logic [DATA_WIDTH-1:0]   wdata_b_i,
    input logic                    we_b_i,

    // Output error simple parity
    output logic error_o_rf_tag
);

  localparam NUM_WORDS = 2 ** ADDR_WIDTH;

  logic [NUM_WORDS-1:0][DATA_WIDTH-1:0] rf_reg;
  logic [NUM_WORDS-1:0][DATA_WIDTH-1:0] rf_sp;
  logic                                 rf_reg_sp;
  logic [NUM_WORDS-1:0]                 we_a_dec;
  logic [NUM_WORDS-1:0]                 we_b_dec;

  always_comb begin : we_a_decoder
    for (int i = 0; i < NUM_WORDS; i++) begin
      if (waddr_a_i == i) we_a_dec[i] = we_a_i;
      else we_a_dec[i] = 1'b0;
    end
  end

  always_comb begin : we_b_decoder
    for (int i = 0; i < NUM_WORDS; i++) begin
      if (waddr_b_i == i) we_b_dec[i] = we_b_i;
      else we_b_dec[i] = 1'b0;
    end
  end

  // loop from 1 to NUM_WORDS-1 as R0 is nil
  always_comb begin : register_write_sp
    for (int j = 0; j < NUM_WORDS; j++) begin : rf_gen_sp
      if (rst_n == 1'b0) begin
        rf_sp[j] = 'b0;
      end else begin
        if (we_b_dec[j] == 1'b1) rf_sp[j] <= wdata_b_i;
        else if (we_a_dec[j] == 1'b1) rf_sp[j] <= wdata_a_i;
        else rf_sp[j] <= rf_reg[j];
      end
    end
  end

  genvar i;
  generate
    for (i = 1; i < NUM_WORDS; i++) begin : rf_gen
      always_ff @(posedge clk, negedge rst_n) begin : register_write_behavioral
        if (rst_n == 1'b0) begin
          rf_reg[i] <= 'b0;
        end else begin
          if (we_b_dec[i] == 1'b1) rf_reg[i] <= wdata_b_i;
          else if (we_a_dec[i] == 1'b1) rf_reg[i] <= wdata_a_i;
        end
      end
    end

    // R0 is nil
    assign rf_reg[0] = '0;
  endgenerate

  riscv_simple_parity_encoder_rf_tag simple_parity_encoder_rf_tag (
      .clk          ( clk       ),
      .rst_n        ( rst_n     ),
      .reg_i        ( rf_sp     ),
      .sp_o_rf_tag  ( rf_reg_sp )
  );

  riscv_simple_parity_decoder_rf_tag simple_parity_decoder_rf_tag (
      .rst_n          ( rst_n           ),
      .reg_i          ( rf_reg          ),
      .sp_i           ( rf_reg_sp       ),
      .error_o_rf_tag ( error_o_rf_tag  )
  );

  assign rdata_a_o = rf_reg[raddr_a_i];
  assign rdata_b_o = rf_reg[raddr_b_i];
  assign rdata_c_o = rf_reg[raddr_c_i];

endmodule