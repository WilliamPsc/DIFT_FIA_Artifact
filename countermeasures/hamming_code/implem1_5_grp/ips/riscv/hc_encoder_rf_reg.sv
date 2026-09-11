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

module riscv_hamming_code_encoder_rf_reg #(
    parameter DATA_WIDTH = 1
) (
    input logic        clk,
    input logic        rst_n,
    // Input
    input logic [31:0] hc_i,

    // Output
    output logic [5:0] hc_o_rf_tag
);
  logic [37:0][DATA_WIDTH-1:0] hc_t;

  always_comb begin
    if ((rst_n == 1'b1)) begin
      hc_t = {
        hc_i[31:26], 1'b0, hc_i[25:11], 1'b0, hc_i[10:4], 1'b0, hc_i[3:1], 1'b0, hc_i[0], 1'b0, 1'b0
      };

      hc_t[0] = hc_t[2] ^ hc_t[4] ^ hc_t[6] ^ hc_t[8] ^ hc_t[10] ^ hc_t[12] ^ hc_t[14] ^ hc_t[16] ^ hc_t[18] ^ hc_t[20] ^ hc_t[22] ^ hc_t[24] ^ hc_t[26] ^ hc_t[28] ^ hc_t[30] ^ hc_t[32] ^ hc_t[34] ^ hc_t[36];
      hc_t[1] = hc_t[2] ^ hc_t[5] ^ hc_t[6] ^ hc_t[9] ^ hc_t[10] ^ hc_t[13] ^ hc_t[14] ^ hc_t[17] ^ hc_t[18] ^ hc_t[21] ^ hc_t[22] ^ hc_t[25] ^ hc_t[26] ^ hc_t[29] ^ hc_t[30] ^ hc_t[33] ^ hc_t[34] ^ hc_t[37];
      hc_t[3] = hc_t[4] ^ hc_t[5] ^ hc_t[6] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30] ^ hc_t[35] ^ hc_t[36] ^ hc_t[37];
      hc_t[7] = hc_t[8] ^ hc_t[9] ^ hc_t[10] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
      hc_t[15] = hc_t[16] ^ hc_t[17] ^ hc_t[18] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
      hc_t[31] = hc_t[32] ^ hc_t[33] ^ hc_t[34] ^ hc_t[35] ^ hc_t[36] ^ hc_t[37];
    end
  end

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      hc_o_rf_tag <= '0;
    end else begin
      hc_o_rf_tag = {hc_t[31], hc_t[15], hc_t[7], hc_t[3], hc_t[1], hc_t[0]};
    end
  end
endmodule

// 000000X000000000000000X0000000X000X0XX
// XXXXXX00000000000000000000000000000000
