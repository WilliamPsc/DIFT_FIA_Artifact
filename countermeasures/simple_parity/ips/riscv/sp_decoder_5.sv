// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - decoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take a register of 5 bits in input                         //
//                 Integrate simple parity values in the right place          //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_simple_parity_decoder_5 #(
) (
    input logic       rst_n,
    // Input
    input logic       sp_i,
    input logic [4:0] reg_i,

    // Output
    output logic error_o_addr_rf_tag
);
  logic sp_t;

  always_comb begin
    if (rst_n) begin
      sp_t = ^reg_i;
      error_o_addr_rf_tag = {sp_t != sp_i};
    end
  end
endmodule
// 0X000X0XX
