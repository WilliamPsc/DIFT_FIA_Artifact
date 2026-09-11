// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - decoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take a register of 5 bits in input                        //
//                 Integrate hamming values in the right place                //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_hamming_code_decoder_5 #(
) (
    input logic       rst_n,
    // Input
    input logic [3:0] hc_i,
    input logic [4:0] reg_i,

    // Output
    output logic       sec_interrupt,
    output logic [4:0] reg_o_corr
);
  logic hc_1, hc_2, hc_4, hc_8;
  logic [8:0] hc_t;
  logic [3:0] error;

  always_comb begin
    if (rst_n) begin
      hc_t  = {reg_i[4], hc_i[3], reg_i[3:1], hc_i[2], reg_i[0], hc_i[1], hc_i[0]};
      hc_1  = hc_t[2] ^ hc_t[4] ^ hc_t[6] ^ hc_t[8];
      hc_2  = hc_t[2] ^ hc_t[5] ^ hc_t[6];
      hc_4  = hc_t[4] ^ hc_t[5] ^ hc_t[6];
      hc_8  = hc_t[8];

      error = {hc_i[3] != hc_8, hc_i[2] != hc_4, hc_i[1] != hc_2, hc_i[0] != hc_1};
      if (error == 4'b0000) begin
        reg_o_corr = reg_i;
      end else begin
        hc_t[error-1'b1] = hc_t[error-1'b1] ^ 1;
        reg_o_corr = {hc_t[8], hc_t[6:4], hc_t[2]};
        sec_interrupt = 1'b1;
      end
    end
  end
endmodule
// 0X000X0XX
