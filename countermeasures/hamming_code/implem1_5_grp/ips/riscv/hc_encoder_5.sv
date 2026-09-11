// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - encoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take a register of 5 bits in input                        //
//                 Integrate hamming values in the right place                //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_hamming_code_encoder_5 #(
) (
    input logic clk,
    input logic rst_n,

    // Input
    input logic [4:0] reg_i,

    // Output
    output logic [3:0] hc_o_5
);

  logic [8:0] hc_t;

  always_comb begin
    if (rst_n) begin
      hc_t = {reg_i[4], 1'b0, reg_i[3:1], 1'b0, reg_i[0], 1'b0, 1'b0};
      hc_t[0] = hc_t[2] ^ hc_t[4] ^ hc_t[6] ^ hc_t[8];
      hc_t[1] = hc_t[2] ^ hc_t[5] ^ hc_t[6];
      hc_t[3] = hc_t[4] ^ hc_t[5] ^ hc_t[6];
      hc_t[7] = hc_t[8];
    end
  end

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      hc_o_5 <= '0;
    end else begin
      hc_o_5 <= {hc_t[7], hc_t[3], hc_t[1], hc_t[0]};
    end
  end
endmodule
// 0X000X0XX
