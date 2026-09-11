// Copyright 2023 SUPSI Lugano & UBS Lorient.
////////////////////////////////////////////////////////////////////////////////
// Engineer        William PENSEC - william.pensec@univ-ubs.fr                //
//                                                                            //
// Design Name:    Hamming code - encoder                                     //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Take 21 registers for 27 bits in input                     //
//                 Integrate hamming values in the right place                //
//                 Do the operation on the bits to calculate                  //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

module riscv_hamming_code_encoder_26 #(
) (
    input logic clk,
    input logic rst_n,

    // Input
    input logic       pc_if_i_tag,               //
    input logic       pc_id_i_tag,               // 
    input logic [1:0] alu_operator_i_mode,       // 
    input logic       store_dest_addr_ex_i_tag,  // 
    input logic       store_source_ex_i_tag,     // 
    input logic       use_store_ops_ex_i,        // 
    input logic       alu_operand_a_ex_i_tag,    // 
    input logic       alu_operand_b_ex_i_tag,    // 
    input logic       alu_operand_c_ex_i_tag,    // 
    input logic       check_s1_i_tag,            // 
    input logic       check_s2_i_tag,            // 
    input logic       check_d_i_tag,             // 
    input logic       register_set_i_tag,        // 
    input logic       is_store_post_i_tag,       // 
    input logic       memory_set_i_tag,          // 
    input logic       rs1_i_tag,                 // 
    input logic       data_we_q_i_tag,           // 
    input logic [3:0] rdata_q_i_tag,             // 
    input logic [1:0] rdata_offset_q_i_tag,      // 
    input logic [1:0] data_type_q_i_tag,         // 

    // Output
    output logic [4:0] hc_o_26
);

  logic [30:0] hc_t;

  always_comb begin
    hc_t = {
      rdata_q_i_tag,  // 4
      rdata_offset_q_i_tag,  // 2
      data_type_q_i_tag,  // 2
      data_we_q_i_tag,
      memory_set_i_tag,
      is_store_post_i_tag,
      register_set_i_tag,
      check_d_i_tag,
      check_s2_i_tag,
      check_s1_i_tag,
      1'b0,
      alu_operand_c_ex_i_tag,
      alu_operand_b_ex_i_tag,
      alu_operand_a_ex_i_tag,
      use_store_ops_ex_i,
      store_source_ex_i_tag,
      alu_operator_i_mode,  // 2
      1'b0,
      store_dest_addr_ex_i_tag,
      rs1_i_tag,
      pc_id_i_tag,
      1'b0,
      pc_if_i_tag,
      1'b0,
      1'b0
    };

    hc_t[0] = hc_t[2] ^ hc_t[4] ^ hc_t[6] ^ hc_t[8] ^ hc_t[10] ^ hc_t[12] ^ hc_t[14] ^ hc_t[16] ^ hc_t[18] ^ hc_t[20] ^ hc_t[22] ^ hc_t[24] ^ hc_t[26] ^ hc_t[28] ^ hc_t[30];
    hc_t[1] = hc_t[2] ^ hc_t[5] ^ hc_t[6] ^ hc_t[9] ^ hc_t[10] ^ hc_t[13] ^ hc_t[14] ^ hc_t[17] ^ hc_t[18] ^ hc_t[21] ^ hc_t[22] ^ hc_t[25] ^ hc_t[26] ^ hc_t[29] ^ hc_t[30];
    hc_t[3] = hc_t[4] ^ hc_t[5] ^ hc_t[6] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
    hc_t[7] = hc_t[8] ^ hc_t[9] ^ hc_t[10] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
    hc_t[15] = hc_t[16] ^ hc_t[17] ^ hc_t[18] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
  end
  

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      hc_o_26 <= '0;
    end else begin
      hc_o_26 <= {hc_t[15], hc_t[7], hc_t[3], hc_t[1], hc_t[0]};
    end
  end
endmodule

// 000000000000000X0000000X000X0XX
