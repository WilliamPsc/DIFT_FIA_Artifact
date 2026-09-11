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

module riscv_simple_parity_encoder_26 #(
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
    output logic      sp_o_26
);

  logic [25:0] sp_t;
  logic        sp_tm;

  always_comb begin
    sp_t = {
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
      alu_operand_c_ex_i_tag,
      alu_operand_b_ex_i_tag,
      alu_operand_a_ex_i_tag,
      use_store_ops_ex_i,
      store_source_ex_i_tag,
      alu_operator_i_mode,  // 2
      store_dest_addr_ex_i_tag,
      rs1_i_tag,
      pc_id_i_tag,
      pc_if_i_tag
    };

    sp_tm = ^sp_t;
  end
  

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      sp_o_26 <= '0;
    end else begin
      sp_o_26 <= sp_tm;
    end
  end
endmodule

// 000000000000000X0000000X000X0XX
