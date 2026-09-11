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

module riscv_hamming_code_decoder_26 #(
) (
    input logic       rst_n,
    // Input
    input logic [4:0] hc_i,

    input logic       pc_if_i_tag,
    input logic       pc_id_i_tag,
    input logic [1:0] alu_operator_i_mode,
    input logic       store_dest_addr_ex_i_tag,
    input logic       store_source_ex_i_tag,
    input logic       use_store_ops_ex_i,
    input logic       alu_operand_a_ex_i_tag,
    input logic       alu_operand_b_ex_i_tag,
    input logic       alu_operand_c_ex_i_tag,
    input logic       check_s1_i_tag,
    input logic       check_s2_i_tag,
    input logic       check_d_i_tag,
    input logic       register_set_i_tag,
    input logic       is_store_post_i_tag,
    input logic       memory_set_i_tag,
    input logic       rs1_i_tag,
    input logic       data_we_q_i_tag,
    input logic [3:0] rdata_q_i_tag,
    input logic [1:0] rdata_offset_q_i_tag,
    input logic [1:0] data_type_q_i_tag,

    // Output
    output logic       pc_if_o_tag_corr,
    output logic       pc_id_o_tag_corr,
    output logic [1:0] alu_operator_o_mode_corr,
    output logic       store_dest_addr_ex_o_tag_corr,
    output logic       store_source_ex_o_tag_corr,
    output logic       use_store_ops_ex_o_corr,
    output logic       alu_operand_a_ex_o_tag_corr,
    output logic       alu_operand_b_ex_o_tag_corr,
    output logic       alu_operand_c_ex_o_tag_corr,
    output logic       check_s1_o_tag_corr,
    output logic       check_s2_o_tag_corr,
    output logic       check_d_o_tag_corr,
    output logic       register_set_o_tag_corr,
    output logic       is_store_post_o_tag_corr,
    output logic       memory_set_o_tag_corr,
    output logic       rs1_o_tag_corr,
    output logic       data_we_q_o_tag_corr,
    output logic [3:0] rdata_q_o_tag_corr,
    output logic [1:0] rdata_offset_q_o_tag_corr,
    output logic [1:0] data_type_q_o_tag_corr,
    output logic       sec_interrupt
);
  logic [30:0] hc_t;
  logic hc_1, hc_2, hc_4, hc_8, hc_16;
  logic [4:0] error;

  always_comb begin
    if ((rst_n)) begin
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
        hc_i[4],
        alu_operand_c_ex_i_tag,
        alu_operand_b_ex_i_tag,
        alu_operand_a_ex_i_tag,
        use_store_ops_ex_i,
        store_source_ex_i_tag,
        alu_operator_i_mode,  // 2
        hc_i[3],
        store_dest_addr_ex_i_tag,
        rs1_i_tag,
        pc_id_i_tag,
        hc_i[2],
        pc_if_i_tag,
        hc_i[1],
        hc_i[0]
      };

      hc_1 = hc_t[2] ^ hc_t[4] ^ hc_t[6] ^ hc_t[8] ^ hc_t[10] ^ hc_t[12] ^ hc_t[14] ^ hc_t[16] ^ hc_t[18] ^ hc_t[20] ^ hc_t[22] ^ hc_t[24] ^ hc_t[26] ^ hc_t[28] ^ hc_t[30];
      hc_2 = hc_t[2] ^ hc_t[5] ^ hc_t[6] ^ hc_t[9] ^ hc_t[10] ^ hc_t[13] ^ hc_t[14] ^ hc_t[17] ^ hc_t[18] ^ hc_t[21] ^ hc_t[22] ^ hc_t[25] ^ hc_t[26] ^ hc_t[29] ^ hc_t[30];
      hc_4 = hc_t[4] ^ hc_t[5] ^ hc_t[6] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
      hc_8 = hc_t[8] ^ hc_t[9] ^ hc_t[10] ^ hc_t[11] ^ hc_t[12] ^ hc_t[13] ^ hc_t[14] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];
      hc_16 = hc_t[16] ^ hc_t[17] ^ hc_t[18] ^ hc_t[19] ^ hc_t[20] ^ hc_t[21] ^ hc_t[22] ^ hc_t[23] ^ hc_t[24] ^ hc_t[25] ^ hc_t[26] ^ hc_t[27] ^ hc_t[28] ^ hc_t[29] ^ hc_t[30];

      error = {
        hc_t[15] != hc_16, hc_t[7] != hc_8, hc_t[3] != hc_4, hc_t[1] != hc_2, hc_t[0] != hc_1
      };

      if (error == 5'b00000) begin
        hc_t = hc_t;
      end else begin
        hc_t[error-1'b1] = hc_t[error-1'b1] ^ 1;
        sec_interrupt = 1'b1;
      end

      pc_if_o_tag_corr = hc_t[2];
      pc_id_o_tag_corr = hc_t[4];
      rs1_o_tag_corr = hc_t[5];
      store_dest_addr_ex_o_tag_corr = hc_t[6];
      alu_operator_o_mode_corr = hc_t[9:8];
      store_source_ex_o_tag_corr = hc_t[10];
      use_store_ops_ex_o_corr = hc_t[11];
      alu_operand_a_ex_o_tag_corr = hc_t[12];
      alu_operand_b_ex_o_tag_corr = hc_t[13];
      alu_operand_c_ex_o_tag_corr = hc_t[14];
      check_s1_o_tag_corr = hc_t[16];
      check_s2_o_tag_corr = hc_t[17];
      check_d_o_tag_corr = hc_t[18];
      register_set_o_tag_corr = hc_t[19];
      is_store_post_o_tag_corr = hc_t[20];
      memory_set_o_tag_corr = hc_t[21];
      data_we_q_o_tag_corr = hc_t[22];
      data_type_q_o_tag_corr = hc_t[24:23];
      rdata_offset_q_o_tag_corr = hc_t[26:25];
      rdata_q_o_tag_corr = hc_t[30:27];
    end
  end
endmodule
