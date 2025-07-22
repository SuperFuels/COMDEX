-- File: backend/modules/codex/hardware/codex_core.vhd
-- Description: Symbolic Virtual CPU core definition for CodexCore
-- Symbolic HDL emulating register logic, glyph operators, control flow, memory, and collapse states

entity CodexCore is
    port (
        clk : in std_logic;
        reset : in std_logic;
        glyph_in : in std_logic_vector(15 downto 0);
        context_in : in std_logic_vector(255 downto 0);
        glyph_out : out std_logic_vector(15 downto 0);
        trace_out : out std_logic_vector(255 downto 0)
    );
end CodexCore;

architecture Behavioral of CodexCore is

    -- === Register Bank ===
    type reg_array is array(0 to 15) of std_logic_vector(63 downto 0);
    signal registers : reg_array := (others => (others => '0'));

    -- === Instruction Buffer ===
    signal instruction : std_logic_vector(15 downto 0);
    signal opcode : std_logic_vector(3 downto 0);
    signal operand_a : std_logic_vector(3 downto 0);
    signal operand_b : std_logic_vector(3 downto 0);

    -- === Glyph Logic Flags ===
    signal superpose : std_logic := '0';
    signal collapse : std_logic := '0';
    signal entangle  : std_logic := '0';
    signal symbolic_tick : std_logic := '0';

begin

    process(clk, reset)
    begin
        if reset = '1' then
            registers <= (others => (others => '0'));
            glyph_out <= (others => '0');
            trace_out <= (others => '0');

        elsif rising_edge(clk) then
            instruction <= glyph_in;
            opcode <= glyph_in(15 downto 12);
            operand_a <= glyph_in(11 downto 8);
            operand_b <= glyph_in(7 downto 4);

            -- === Symbolic Opcode Handling ===
            case opcode is

                -- ⊕ EXECUTE: Register A = A ⊕ B (symbolic add)
                when "0001" =>
                    registers(to_integer(unsigned(operand_a))) <=
                        registers(to_integer(unsigned(operand_a))) xor
                        registers(to_integer(unsigned(operand_b)));

                -- → MOVE: A = B
                when "0010" =>
                    registers(to_integer(unsigned(operand_a))) <=
                        registers(to_integer(unsigned(operand_b)));

                -- ⟲ MUTATE: A = MUTATE(A)
                when "0011" =>
                    registers(to_integer(unsigned(operand_a))) <= not registers(to_integer(unsigned(operand_a)));

                -- ↔ ENTANGLE: Set entangle flag
                when "0100" =>
                    entangle <= '1';

                -- ⧖ COLLAPSE: Set collapse flag
                when "0101" =>
                    collapse <= '1';

                -- 🌀 SUPERPOSE: Enable superposition
                when "0110" =>
                    superpose <= '1';

                -- 🧠 CONTEXTUAL: Feed in external context
                when "0111" =>
                    registers(0) <= context_in(63 downto 0);

                -- 💾 MEMORY WRITE: RegA → Memory (to be implemented in CodexMemory.vhd)
                when "1000" =>
                    null; -- placeholder

                -- DEFAULT
                when others =>
                    null;
            end case;

            -- Output state
            glyph_out <= instruction;
            trace_out(255 downto 192) <= registers(0); -- Trace reg[0]
            trace_out(191 downto 128) <= registers(1);
            trace_out(127 downto 0) <= context_in(127 downto 0);

        end if;
    end process;

end Behavioral;
