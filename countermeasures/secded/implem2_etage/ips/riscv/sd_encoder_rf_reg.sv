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

module riscv_secded_encoder_rf_reg #(
    parameter DATA_WIDTH = 1,
    REG_SIZE = 32,
    HC_SIZE = 6,
    G_PARITY
) (
    // Input
    input logic                clk,
    input logic [REG_SIZE-1:0] reg_i,

    // Output
    output logic               sd_o_rf_tag,
    output logic [HC_SIZE-1:0] hc_o_rf_tag
);
  logic [REG_SIZE+HC_SIZE-1:0][DATA_WIDTH-1:0] hc_t;
  logic                                        secded = 1'b0;

  always_comb begin
    // Initialisation
    for (int i = 1, j = 0; i < REG_SIZE + HC_SIZE + 1; i++) begin
      if ((i & (i - 1)) == 0) begin
        // If the current index is a power of 2, set the flag to true
        hc_t[i-1] = 1'b0;
      end else begin
        hc_t[i-1] = reg_i[j];
        j++;
      end
    end

    // Encode
    for (int j = 0; j < HC_SIZE; j++) begin
      for (int i = 1; i < REG_SIZE + HC_SIZE + 1; i++) begin
        // Extract jth bit of i and compare
        if (i[j] == 1'b1) begin
          hc_t[(2**j)-1] ^= hc_t[i-1];
        end
      end
    end

    // Compute secded
    if (G_PARITY == 1) begin
      // $display("SECDED ACTIF ENCODER");
      secded = 1'b0;
      for (int k = 0; k < REG_SIZE + HC_SIZE; k++) begin
        secded ^= hc_t[k];
      end
    end
  end

  always_ff @(posedge clk) begin
    if (G_PARITY == 1) begin
      sd_o_rf_tag <= secded;
    end else begin
      sd_o_rf_tag <= 1'b0;
    end
    for (int i = 0; i < HC_SIZE; i++) begin
      hc_o_rf_tag[i] <= hc_t[(2**i)-1];
    end
  end
endmodule
