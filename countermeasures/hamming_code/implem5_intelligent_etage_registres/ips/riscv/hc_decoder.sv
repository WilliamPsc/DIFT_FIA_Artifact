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


module riscv_hamming_code_decoder #(
    parameter REG_SIZE,
    HC_SIZE
) (
    // Input
    input logic [REG_SIZE-1:0] reg_i,
    input logic [ HC_SIZE-1:0] hc_i,

    // Output
    output logic [REG_SIZE-1:0] reg_o_corr,
    output logic                sec_interrupt
);

  // intern signals
  logic [           HC_SIZE-1:0] hc_redundancy = '0;
  logic [REG_SIZE + HC_SIZE-1:0] hc_t = '0;

  always_comb begin
    hc_redundancy = '0;  // if no init to 0 the signal stay to 'X'

    // Placement redundancy bits in hc_t
    for (int i = 1, j = 0, k = 0; i < REG_SIZE + HC_SIZE + 1; i++) begin
      if ((i & (i - 1)) == 0) begin
        // If the current index is a power of 2, set the flag to true
        hc_t[i-1] = hc_i[k];
        k++;
      end else begin
        hc_t[i-1] = reg_i[j];
        j++;
      end
    end

    // calcul redundancy
    for (int j = 0; j < HC_SIZE; j++) begin
      for (int i = 1; i < REG_SIZE + HC_SIZE + 1; i++) begin
        if (i[j] == 1'b1) begin
          if (i == 1) begin
            hc_redundancy[j] = hc_t[i-1];
          end else begin
            hc_redundancy[j] ^= hc_t[i-1];
          end
        end
      end
    end

    
    if (hc_redundancy == '0) begin
      // No errors detected and corrected
      // $display("Hamming Decode : No error");
      reg_o_corr = reg_i;
      sec_interrupt = 1'b0;
    end else begin
      // Single Error Correction, Single error detection
      // $display("Hamming Decode : SEC");
      hc_t[hc_redundancy-1'b1] = hc_t[hc_redundancy-1'b1] ^ 1;  // inversion de bit
      for (int i = 1, j = 0; i < REG_SIZE + HC_SIZE + 1; i++) begin
        if ((i & (i - 1)) != 0) begin
          reg_o_corr[j] = hc_t[i-1];
          j++;
        end
      end
      sec_interrupt = 1'b1;
    end
  end
endmodule