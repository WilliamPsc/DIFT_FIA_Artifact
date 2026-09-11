// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - encoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take a register of 32 bits in input                        //
//                 Integrate hamming values in the right place                //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_simple_parity_encoder_rf_tag #(
) (
    input logic        clk,
    input logic        rst_n,
    // Input
    input logic [31:0] reg_i,

    // Output
    output logic sp_o_rf_tag
);
  logic sp_t;

  always_comb begin
    if (rst_n) begin
      sp_t = ^reg_i;
    end
  end

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      sp_o_rf_tag <= '0;
    end else begin
      sp_o_rf_tag <= sp_t;
    end
  end
endmodule

// 000000X000000000000000X0000000X000X0XX
// XXXXXX00000000000000000000000000000000
