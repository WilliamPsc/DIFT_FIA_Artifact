// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - decoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take a register of 32 bits in input                        //
//                 Integrate hamming values in the right place                //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_hamming_code_decoder_32 #(
) (
    input logic        rst_n,
    // Input
    input logic [31:0] reg_i,
    input logic [ 4:0] hc_i,

    // Output
    output logic        sec_interrupt,
    output logic [31:0] hc_o_corr
);
  logic hc_1, hc_2, hc_4, hc_8, hc_16;
  logic [31:0] hc_t;
  logic [ 4:0] error;

  always_comb begin
    if (rst_n) begin
      hc_t = {
        reg_i[26:11], hc_i[4], reg_i[10:4], hc_i[3], reg_i[3:1], hc_i[2], reg_i[0], hc_i[1], hc_i[0]
      };
      hc_1 = hc_t[2] ^ hc_t[4] ^ hc_t[6] ^ hc_t[8] ^ hc_t[10] ^ hc_t[12] ^ hc_t[14] ^ hc_t[16] ^ hc_t[18] ^ hc_t[20] ^ hc_t[22] ^ hc_t[24] ^ hc_t[26] ^ hc_t[28] ^ hc_t[30];
      hc_2 = hc_t[2] ^ hc_t[5] ^ hc_t[6] ^ hc_t[9] ^ hc_t[10] ^ hc_t[13] ^ hc_t[14] ^ hc_t[17] ^ hc_t[18] ^ hc_t[21] ^ hc_t[22] ^ hc_t[25] ^ hc_t[26] ^ hc_t[29] ^ hc_t[30];
      hc_4 = hc_t[4] ^ hc_t[5] ^ hc_t[6] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
      hc_8 = hc_t[8] ^ hc_t[9] ^ hc_t[10] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
      hc_16 = hc_t[16] ^ hc_t[17] ^ hc_t[18] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];

      error = {
        hc_i[4] != hc_16, hc_i[3] != hc_8, hc_i[2] != hc_4, hc_i[1] != hc_2, hc_i[0] != hc_1
      };
      if (error == 5'b00000) begin
        hc_o_corr = reg_i;
      end else begin
        hc_t[error-1'b1] = hc_t[error-1'b1] ^ 1;
        hc_o_corr = {hc_t[31:16], hc_t[14:8], hc_t[6:4], hc_t[2]};
        sec_interrupt = 1'b1;
      end
    end
  end
endmodule
