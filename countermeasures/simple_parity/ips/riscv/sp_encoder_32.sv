// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - encoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take a register of 32 bits in input                        //
//                 Integrate simple parity  values in the right place         //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_simple_parity_encoder_32 #(
) (
    input logic clk,
    input logic rst_n,

    // Input
    input logic [31:0] reg_i,

    // Output
    output logic sp_o_32
);

  logic sp_t = '0;

  always_comb begin
    sp_t = ^reg_i;
  end

  always_ff @(posedge clk, negedge rst_n) begin
    sp_o_32 <= sp_t;
  end
endmodule
