#==================================================================================
# IMPORT
#==================================================================================
import sys
import pygame
import numpy as np
import time

keys = [0] * 256

#==================================================================================
# PARSER
#==================================================================================

class romLoader:
    rom = 0

    def __init__(self, romPath):
        self.rom = self.openFile(romPath)

    def openFile(self, romPath):
        rom = open(romPath, 'rb')
        return rom

    def load(self):
        if(self.rom.read(3).decode('ascii') != 'NES'):
            exit()
        self.rom.seek(4)

        self.prgRomCount =  ord(self.rom.read(1))
        self.chrRomCount =  ord(self.rom.read(1))
        self.flags6 = ord(self.rom.read(1))
        self.flags7 = ord(self.rom.read(1))
        self.prgRamCount = ord(self.rom.read(1))
        self.flags9 = ord(self.rom.read(1))
        self.flags10 = ord(self.rom.read(1))

        self.mapperNumber = ((self.flags6 & 240) >> 4) + (self.flags7 & 240)

        self.rom.seek(16)

        if self.flags6 & 4:
            self.trainerData = self.rom.read(0x200)

        self.mirror = self.flags6 & 1

        self.prgRomData = list(self.rom.read(0x4000 * self.prgRomCount))
        self.chrRomData = list(self.rom.read(0x2000 * self.chrRomCount))

#==================================================================================
# CPU
#==================================================================================

class cpu:
    def __init__(self, cartridge):
        self.ppu = ppu(self, cartridge)

        self.registers = {
            'PC': 0,            # Program Counter
            'SP': 0xFF,         # Stack Pointer
            'A': 0,             # Accumulator
            'X': 0,             # Register X
            'Y': 0,             # Register Y
            'P': 0b00100000     # Processor Status
        }

        self.statusFlags = {
            'c': 0,      # Carry Flag
            'z': 1,      # Zero Flag
            'i': 2,      # Interrupt Disable
            'd': 3,      # Decimal Mode
            'b': 4,      # Break Command
            'v': 6,      # Overflow Flag
            'n': 7       # Negative Flag
        }

        self.memory = [0x00] * 0x10000
        self.scanline = 0
        self.cart = cartridge
        self.initMemory()
        self.registers['PC'] = self.dmaRAMRead(0xFFFC) | (self.dmaRAMRead(0xFFFD) << 8)
        self.count = 0
        self.z = 0

        self.instructions = {   0x00: BRK_Implied, 
                                0x01: ORA_Indirect_X, 
                                0x05: ORA_Zero, 
                                0x06: ASL_Zero, 
                                0x08: PHP_Implied, 
                                0x09: ORA_Immediate, 
                                0x0A: ASL_Accumulator, 
                                0x0D: ORA_Absolute, 
                                0x0E: ASL_Absolute, 
                                0x10: BPL_Relative, 
                                0x11: ORA_Indirect_Y, 
                                0x15: ORA_Zero_X, 
                                0x16: ASL_Zero_X, 
                                0x18: CLC_Implied, 
                                0x19: ORA_Absolute_Y, 
                                0x1D: ORA_Absolute_X, 
                                0x1E: ASL_Absolute_X, 
                                0x20: JSR_Absolute, 
                                0x21: AND_Indirect_X, 
                                0x24: BIT_Zero, 
                                0x25: AND_Zero, 
                                0x26: ROL_Zero, 
                                0x28: PLP_Implied, 
                                0x29: AND_Immediate, 
                                0x2A: ROL_Accumulator, 
                                0x2C: BIT_Absolute, 
                                0x2D: AND_Absolute, 
                                0x2E: ROL_Absolute, 
                                0x30: BMI_Relative, 
                                0x31: AND_Indirect_Y, 
                                0x35: AND_Zero_X, 
                                0x36: ROL_Zero_X, 
                                0x38: SEC_Implied, 
                                0x39: AND_Absolute_Y, 
                                0x3D: AND_Absolute_X, 
                                0x3E: ROL_Absolute_X, 
                                0x40: RTI_Implied, 
                                0x41: EOR_Indirect_X, 
                                0x45: EOR_Zero, 
                                0x46: LSR_Zero, 
                                0x48: PHA_Implied, 
                                0x49: EOR_Immediate, 
                                0x4A: LSR_Accumulator, 
                                0x4C: JMP_Absolute, 
                                0x4D: EOR_Absolute, 
                                0x4E: LSR_Absolute, 
                                0x50: BVC_Relative, 
                                0x51: EOR_Indirect_Y, 
                                0x55: EOR_Zero_X, 
                                0x56: LSR_Zero_X, 
                                0x58: CLI_Implied, 
                                0x59: EOR_Absolute_Y, 
                                0x5D: EOR_Absolute_X, 
                                0x5E: LSR_Absolute_X, 
                                0x60: RTS_Implied, 
                                0x61: ADC_Indirect_X, 
                                0x65: ADC_Zero, 
                                0x66: ROR_Zero, 
                                0x68: PLA_Implied, 
                                0x69: ADC_Immediate, 
                                0x6A: ROR_Accumulator, 
                                0x6C: JMP_Indirect, 
                                0x6D: ADC_Absolute, 
                                0x6E: ROR_Absolute, 
                                0x70: BVS_Relative, 
                                0x71: ADC_Indirect_Y, 
                                0x75: ADC_Zero_X, 
                                0x76: ROR_Zero_X, 
                                0x78: SEI_Implied, 
                                0x79: ADC_Absolute_Y, 
                                0x7D: ADC_Absolute_X, 
                                0x7E: ROR_Absolute_X, 
                                0x81: STA_Indirect_X, 
                                0x84: STY_Zero, 
                                0x85: STA_Zero, 
                                0x86: STX_Zero, 
                                0x88: DEY_Implied, 
                                0x8A: TXA_Implied, 
                                0x8C: STY_Absolute, 
                                0x8D: STA_Absolute, 
                                0x8E: STX_Absolute, 
                                0x90: BCC_Relative, 
                                0x91: STA_Indirect_Y, 
                                0x94: STY_Zero_X, 
                                0x95: STA_Zero_X, 
                                0x96: STX_Zero_Y, 
                                0x98: TYA_Implied, 
                                0x99: STA_Absolute_Y, 
                                0x9A: TXS_Implied, 
                                0x9D: STA_Absolute_X, 
                                0xA0: LDY_Immediate, 
                                0xA1: LDA_Indirect_X, 
                                0xA2: LDX_Immediate, 
                                0xA4: LDY_Zero, 
                                0xA5: LDA_Zero, 
                                0xA6: LDX_Zero, 
                                0xA8: TAY_Implied, 
                                0xA9: LDA_Immediate, 
                                0xAA: TAX_Implied, 
                                0xAC: LDY_Absolute, 
                                0xAD: LDA_Absolute, 
                                0xAE: LDX_Absolute, 
                                0xB0: BCS_Relative, 
                                0xB1: LDA_Indirect_Y, 
                                0xB4: LDY_Zero_X, 
                                0xB5: LDA_Zero_X, 
                                0xB6: LDX_Zero_Y, 
                                0xB8: CLV_Implied, 
                                0xB9: LDA_Absolute_Y, 
                                0xBA: TSX_Implied, 
                                0xBC: LDY_Absolute_X, 
                                0xBD: LDA_Absolute_X, 
                                0xBE: LDX_Absolute_Y, 
                                0xC0: CPY_Immediate, 
                                0xC1: CMP_Indirect_X, 
                                0xC4: CPY_Zero, 
                                0xC5: CMP_Zero, 
                                0xC6: DEC_Zero, 
                                0xC8: INY_Implied, 
                                0xC9: CMP_Immediate, 
                                0xCA: DEX_Implied, 
                                0xCC: CPY_Absolute, 
                                0xCD: CMP_Absolute, 
                                0xCE: DEC_Absolute, 
                                0xD0: BNE_Relative, 
                                0xD1: CMP_Indirect_Y, 
                                0xD5: CMP_Zero_X, 
                                0xD6: DEC_Zero_X, 
                                0xD8: CLD_Implied, 
                                0xD9: CMP_Absolute_Y, 
                                0xDD: CMP_Absolute_X, 
                                0xDE: DEC_Absolute_X, 
                                0xE0: CPX_Immediate, 
                                0xE1: SBC_Indirect_X, 
                                0xE4: CPX_Zero, 
                                0xE5: SBC_Zero, 
                                0xE6: INC_Zero, 
                                0xE8: INX_Implied, 
                                0xE9: SBC_Immediate, 
                                0xEA: NOP_Implied, 
                                0xEC: CPX_Absolute, 
                                0xED: SBC_Absolute, 
                                0xEE: INC_Absolute, 
                                0xF0: BEQ_Relative, 
                                0xF1: SBC_Indirect_Y, 
                                0xF5: SBC_Zero_X, 
                                0xF6: INC_Zero_X, 
                                0xF8: SED_Implied, 
                                0xF9: SBC_Absolute_Y, 
                                0xFD: SBC_Absolute_X, 
                                0xFE: INC_Absolute_X, 

                                #Unofficial OpCodes
                                0x03: SLO_Indirect_X, 
                                0x04: DOP_Zero, 
                                0x07: SLO_Zero, 
                                0x0C: TOP_Absolute, 
                                0x0F: SLO_Absolute, 
                                0x13: SLO_Indirect_Y, 
                                0x14: DOP_Zero_X, 
                                0x17: SLO_Zero_X, 
                                0x1A: NOP_Implied, 
                                0x1B: SLO_Absolute_Y, 
                                0x1C: TOP_Absolute_X, 
                                0x1F: SLO_Absolute_X, 
                                0x23: RLA_Indirect_X, 
                                0x27: RLA_Zero, 
                                0x2F: RLA_Absolute, 
                                0x33: RLA_Indirect_Y, 
                                0x34: DOP_Zero_X, 
                                0x37: RLA_Zero_X, 
                                0x3A: NOP_Implied, 
                                0x3B: RLA_Absolute_Y, 
                                0x3C: TOP_Absolute_X, 
                                0x3F: RLA_Absolute_X, 
                                0x43: SRE_Indirect_X, 
                                0x44: DOP_Zero, 
                                0x47: SRE_Zero, 
                                0x4F: SRE_Absolute, 
                                0x53: SRE_Indirect_Y, 
                                0x54: DOP_Zero_X, 
                                0x57: SRE_Zero_X, 
                                0x5A: NOP_Implied, 
                                0x5B: SRE_Absolute_Y, 
                                0x5C: TOP_Absolute_X, 
                                0x5F: SRE_Absolute_X, 
                                0x63: RRA_Indirect_X, 
                                0x64: DOP_Zero, 
                                0x67: RRA_Zero, 
                                0x6F: RRA_Absolute, 
                                0x73: RRA_Indirect_Y, 
                                0x74: DOP_Zero_X, 
                                0x77: RRA_Zero_X, 
                                0x7A: NOP_Implied, 
                                0x7B: RRA_Absolute_Y, 
                                0x7C: TOP_Absolute_X, 
                                0x7F: RRA_Absolute_X, 
                                0x80: DOP_Immediate, 
                                0x82: DOP_Immediate, 
                                0x83: SAX_Indirect_X, 
                                0x87: SAX_Zero, 
                                0x89: DOP_Immediate, 
                                0x8F: SAX_Absolute, 
                                0x97: SAX_Zero_Y, 
                                0xA3: LAX_Indirect_X, 
                                0xA7: LAX_Zero, 
                                0xAF: LAX_Absolute, 
                                0xB3: LAX_Indirect_Y, 
                                0xB7: LAX_Zero_Y, 
                                0xBF: LAX_Absolute_Y, 
                                0xC2: DOP_Immediate, 
                                0xC3: DCP_Indirect_X, 
                                0xC7: DCP_Zero, 
                                0xCF: DCP_Absolute, 
                                0xD3: DCP_Indirect_Y, 
                                0xD4: DOP_Zero_X, 
                                0xD7: DCP_Zero_X, 
                                0xDA: NOP_Implied, 
                                0xDB: DCP_Absolute_Y, 
                                0xDC: TOP_Absolute_X, 
                                0xDF: DCP_Absolute_X, 
                                0xE2: DOP_Immediate, 
                                0xE3: ISB_Indirect_X, 
                                0xE7: ISB_Zero, 
                                0xEB: SBC_Immediate, 
                                0xEF: ISB_Absolute, 
                                0xF3: ISB_Indirect_Y, 
                                0xF4: DOP_Zero_X, 
                                0xF7: ISB_Zero_X, 
                                0xFA: NOP_Implied, 
                                0xFB: ISB_Absolute_Y, 
                                0xFC: TOP_Absolute_X, 
                                0xFF: ISB_Absolute_X
        }

    def initMemory(self):
        if self.cart.mapperNumber != 0:
            print ("Mapper not available yet")
            exit(1)

        i=0
        maxdata = len(self.cart.prgRomData)
        while i < maxdata:
            v = self.cart.prgRomData[i]
            self.dmaRAMWrite(i + 0x8000, v)
            if self.cart.prgRomCount == 1:
                self.dmaRAMWrite(i + 0xC000, v)
            i+=1
        i=0
        while i < 0x20:
            self.dmaRAMWrite(i + 0x4000, 0xFF)
            i+=1

    def doNMI(self):
        self.pushStack((self.registers['PC'] >> 8) & 0xFF)
        self.pushStack(self.registers['PC'] & 0xFF)
        self.pushStack(self.registers['P'])
        self.registers['PC'] = self.dmaRAMRead(0xFFFA) | (self.dmaRAMRead(0xFFFB) << 8)
        self.z = 1

    def dmaRAMWrite(self, address, value):
        self.memory[address] = value

    def dmaRAMRead(self, address):
        value = self.memory[address]
        return value

    def writeMemory(self, address, value):
        global KeysBuffer__, ReadNumber__, LastWrote___
        if address < 0x2000:
            address &= 0x7FF
            self.dmaRAMWrite(address, value)
        elif 0x2000 <= address < 0x4000:
            # PPU Registers
            address &= 0x2007
            if address == 0x2000:
                self.ppu.processControlReg1(value)
            elif address == 0x2001:
                self.ppu.processControlReg2(value)
            elif address == 0x2003:
                self.ppu.spriteRamAddr = value
            elif address == 0x2004:
                self.ppu.writeSprRam(value)
            elif address == 0x2005:
                self.ppu.processPPUSCROLL(value)
            elif address == 0x2006:
                self.ppu.processPPUADDR(value)
            elif address == 0x2007:
                self.ppu.writeVRAM(value)
            self.dmaRAMWrite(address, value)
        elif 0x4000 <= address < 0x4014 or address == 0x4015:
            pass
        elif address == 0x4014:
            self.ppu.writeSprRamDMA(value)
            self.dmaRAMWrite(address, value)
        elif address == 0x4016 or address == 0x4017:
            if LastWrote___ == 1 and value == 0:
                ReadNumber__ = 0
            LastWrote___ = value
            self.dmaRAMWrite(address, value)
        elif 0x6000 <= address < 0x8000:
            pass
        elif 0x8000 <= address < 0x10000:
            self.dmaRAMWrite(address, value)
        else:
            print('Unhandled RAM write access')

    def readMemory(self, address):
        global KeysBuffer__
        value = 0x00
        if address < 0x2000:
            address &= 0x7FF
            value = self.dmaRAMRead(address)
        elif 0x2000 <= address < 0x4000:
            addrflag = (address-0x2000) & 0xF
            if addrflag == 2:
                value = self.ppu.readStatusFlag()
            elif addrflag == 7:
                value = self.ppu.readVRAM()
            self.dmaRAMWrite(address, value)
        elif address == 0x4016:
            Strobe()
            value = KeysBuffer__
        elif 0x4000 < address < 0x4020:
            value = self.dmaRAMRead(address)
        elif 0x6000 <= address < 0x8000:
            pass
        elif 0x8000 <= address < 0x10000:
            value = self.dmaRAMRead(address)
        else:
           print('Unhandled RAM read access')

        return value

    def setStatus(self, flag, value):
        if value:
            self.registers['P'] |= 1 << flag
        else:
            self.registers['P'] &= ~(1 << flag)

    def getStatus(self, flag):
        if (self.registers['P'] & (1 << flag)) == 0:
            return 0
        else:
            return 1

    def pushStack(self, value):
        self.writeMemory(0x100 + self.registers['SP'], value)
        self.registers['SP'] -= 1

    def pullStack(self):
        self.registers['SP'] += 1
        value = self.readMemory(0x100 + self.registers['SP'])
        return value

    def run(self):
        global keys
        cyclesClock = 0
        a = 0
        loopCounter = 0
        fpsCounter = 0
        cyclesCounter = 0
        timer = time.perf_counter()
        self.z = 0
        while True:
            pygame.event.poll()

            instr = self.dmaRAMRead(self.registers['PC'])
            cycles = self.instructions[instr](self)

            cyclesClock += cycles
            if (time.perf_counter() - timer) > 1:
                fpsCounter = int(loopCounter/100)
                timer = time.perf_counter()
                loopCounter = 0
            cyclesCounter = cyclesClock

            if cyclesClock >= 113:
                cyclesClock = 0
                if 0 <= self.scanline < 240:
                    if self.ppu.VBlank:
                        self.ppu.exitVBlank()
                    self.ppu.doScanline()
                elif self.scanline == 241:
                    self.ppu.debugMsg("FPS: {0}".format(fpsCounter))
                    cyclesCounter = 0
                    self.ppu.enterVBlank()
                    pygame.event.pump()
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_ESCAPE] == 1:
                        pygame.quit()
                        sys.exit()
                elif self.scanline == 261:
                    self.scanline = -1
                self.scanline += 1
                loopCounter+=1

#==================================================================================
# PPU
#==================================================================================

class ppu:
    def __init__(self, cpu, cartridge):
        self.cpu = cpu

        self.VRAM = [np.uint8(0x00)] * 0x10000
        self.SPRRAM = [np.uint8(0x00)] * 0x100

        self.nameTableAddress = 0
        self.incrementAddress = 1
        self.spritePatternTable = 0
        self.backgroundPatternTable = 0
        self.spriteSize = 8
        self.NMI = False
        self.colorMode = True
        self.clippingBackground = False
        self.clippingSprites = False
        self.showBackground = False
        self.showSprites = False
        self.colorIntensity = 0

        self.spriteRamAddr = 0
        self.vRamWrites = 0
        self.scanlineSpriteCount = 0
        self.sprite0Hit = 0
        self.spriteHitOccured = False
        self.VBlank = False
        self.VRAMAddress = 0
        self.VRAMBuffer = 0
        self.firstWrite = True
        self.ppuScrollX = 0
        self.ppuScrollY = 0
        self.ppuStarted = 0

        self.ppuMirroring = 0
        self.addressMirroring = 0

        self.matrix = []

        self.cart = cartridge
        self.initMemory()
        self.setMirroring(self.cart.mirror)

        self.colorPallete = [(0x75, 0x75, 0x75),
                             (0x27, 0x1B, 0x8F),
                             (0x00, 0x00, 0xAB),
                             (0x47, 0x00, 0x9F),
                             (0x8F, 0x00, 0x77),
                             (0xAB, 0x00, 0x13),
                             (0xA7, 0x00, 0x00),
                             (0x7F, 0x0B, 0x00),
                             (0x43, 0x2F, 0x00),
                             (0x00, 0x47, 0x00),
                             (0x00, 0x51, 0x00),
                             (0x00, 0x3F, 0x17),
                             (0x1B, 0x3F, 0x5F),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0xBC, 0xBC, 0xBC),
                             (0x00, 0x73, 0xEF),
                             (0x23, 0x3B, 0xEF),
                             (0x83, 0x00, 0xF3),
                             (0xBF, 0x00, 0xBF),
                             (0xE7, 0x00, 0x5B),
                             (0xDB, 0x2B, 0x00),
                             (0xCB, 0x4F, 0x0F),
                             (0x8B, 0x73, 0x00),
                             (0x00, 0x97, 0x00),
                             (0x00, 0xAB, 0x00),
                             (0x00, 0x93, 0x3B),
                             (0x00, 0x83, 0x8B),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0xFF, 0xFF, 0xFF),
                             (0x3F, 0xBF, 0xFF),
                             (0x5F, 0x97, 0xFF),
                             (0xA7, 0x8B, 0xFD),
                             (0xF7, 0x7B, 0xFF),
                             (0xFF, 0x77, 0xB7),
                             (0xFF, 0x77, 0x63),
                             (0xFF, 0x9B, 0x3B),
                             (0xF3, 0xBF, 0x3F),
                             (0x83, 0xD3, 0x13),
                             (0x4F, 0xDF, 0x4B),
                             (0x58, 0xF8, 0x98),
                             (0x00, 0xEB, 0xDB),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0xFF, 0xFF, 0xFF),
                             (0xAB, 0xE7, 0xFF),
                             (0xC7, 0xD7, 0xFF),
                             (0xD7, 0xCB, 0xFF),
                             (0xFF, 0xC7, 0xFF),
                             (0xFF, 0xC7, 0xDB),
                             (0xFF, 0xBF, 0xB3),
                             (0xFF, 0xDB, 0xAB),
                             (0xFF, 0xE7, 0xA3),
                             (0xE3, 0xFF, 0xA3),
                             (0xAB, 0xF3, 0xBF),
                             (0xB3, 0xFF, 0xCF),
                             (0x9F, 0xFF, 0xF3),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00),
                             (0x00, 0x00, 0x00)]

    def initMemory(self):
        maxdata = len(self.cart.chrRomData)
        for i in range(len(self.cart.chrRomData)):
            v = self.cart.chrRomData[i]
            self.dmaVRAMWrite(i, v)

        pygame.init()
        self.screen = pygame.display.set_mode((256, 240))
        self.layerB = pygame.Surface((256,240))
        self.layerA = pygame.Surface((256,240), pygame.SRCALPHA)
        self.debugLayer = pygame.Surface((256,240), pygame.SRCALPHA)
        self.layerB.fill((0, 0, 0))
        self.layerA.fill((0, 0, 0, 0))
        self.debugLayer.fill((0,0,0,0))
        self.screen.blit(self.layerB, (0,0))
        self.screen.blit(self.layerA, (0,0))
        self.screen.blit(self.debugLayer, (0,0))
        pygame.display.flip()

    def dmaVRAMWrite(self, address, value):
        self.VRAM[address] = value

    def dmaVRAMRead(self, address):
        value = self.VRAM[address]
        return value


    def dmaSPRRAMWrite(self, address, value):
        self.SPRRAM[address] = value

    def dmaSPRRAMRead(self, address):
        value = self.SPRRAM[address]
        return value

    def setMirroring(self, mirroring):
        # 0: horizontal mirroring
        # 1: vertical mirroring
        self.ppuMirroring = mirroring
        self.addressMirroring = 0x400 << self.ppuMirroring

    def processControlReg1(self, value):
        # Check bits 0-1
        aux = value & 0x3
        if aux == 0:
            self.nameTableAddress = 0x2000
        elif aux == 1:
            self.nameTableAddress = 0x2400
        elif aux == 2:
            self.nameTableAddress = 0x2800
        else:
            self.nameTableAddress = 0x2C00

        # Check bit 2
        if value & (1 << 2):
            self.incrementAddress = 32
        else:
            self.incrementAddress = 1

        # Check bit 3
        if value & (1 << 3):
            self.spritePatternTable = 0x1000
        else:
            self.spritePatternTable = 0x0000

        # Check bit 4
        if value & (1 << 4):
            self.backgroundPatternTable = 0x1000
        else:
            self.backgroundPatternTable = 0x0000

        # Check bit 5
        if value & (1 << 5):
            self.spriteSize = 16
        else:
            self.spriteSize = 8

        # Bit 6 not used
        # Check bit 7
        if value & (1 << 7):
            self.NMI = True
        else:
            self.NMI = False

    def processControlReg2(self, value):
        # Check bit 0
        if value & 1:
            self.colorMode = True
        else:
            self.colorMode = False

        # Check bit 1
        if value & (1 << 1):
            self.clippingBackground = True
        else:
            self.clippingBackground = False

        # Check bit 2
        if value & (1 << 2):
            self.clippingSprites = True
        else:
            self.clippingSprites = False

        # Check bit 3
        if value & (1 << 3):
            self.showBackground = True
        else:
            self.showBackground = False

        # Check bit 4
        if value & (1 << 4):
            self.showSprites = True
        else:
            self.showSprites = False

        # Check bits 5-7
        self.colorIntensity = value >> 5

    # process register 0x2005
    def processPPUSCROLL(self, value):
        if self.firstWrite:
            self.ppuScrollX = value
            self.firstWrite = False
        else:
            self.ppuScrollY = value
            self.firstWrite = True

    # process register 0x2006
    def processPPUADDR(self, value):
        if self.firstWrite:
            self.VRAMAddress = (value & 0xFF) << 8
            self.firstWrite = False
        else:
            self.VRAMAddress += (value & 0xFF)
            self.firstWrite = True

    # process register 0x2007 (write)
    def writeVRAM(self, value):
        # NameTable write mirroring.
        if self.VRAMAddress >= 0x2000 and self.VRAMAddress < 0x3F00:
            self.dmaVRAMWrite(self.VRAMAddress + self.addressMirroring, value)
            self.dmaVRAMWrite(self.VRAMAddress, value)

        elif self.VRAMAddress >= 0x3F00 and self.VRAMAddress < 0x3F20:
            if self.VRAMAddress == 0x3F00 or self.VRAMAddress == 0x3F10:
                self.dmaVRAMWrite(0x3F00, value)
                self.dmaVRAMWrite(0x3F04, value)
                self.dmaVRAMWrite(0x3F08, value)
                self.dmaVRAMWrite(0x3F0C, value)
                self.dmaVRAMWrite(0x3F10, value)
                self.dmaVRAMWrite(0x3F14, value)
                self.dmaVRAMWrite(0x3F18, value)
                self.dmaVRAMWrite(0x3F1C, value)
            else:
                self.dmaVRAMWrite(self.VRAMAddress, value)

        self.VRAMAddress += self.incrementAddress

    # process register 0x2007 (read)
    def readVRAM(self):
        value = 0
        address = self.VRAMAddress & 0x3FFF
        if address >= 0x3F00 and address < 0x4000:
            address = 0x3F00 + (address & 0xF)
            self.VRAMBuffer = self.dmaVRAMRead(address)
            value = self.dmaVRAMRead(address)
        elif address < 0x3F00:
            value = self.VRAMBuffer
            self.VRAMBuffer = self.dmaVRAMRead(address)
        self.VRAMAddress += self.incrementAddress

        return value

    def writeSprRam(self, value):
        self.dmaSPRRAMWrite(self.spriteRamAddr,value)
        self.spriteRamAddr = (self.spriteRamAddr + 1) & 0xFF

    def writeSprRamDMA(self, value):
        address = value * 0x100

        i=0
        while i < 256:
            self.dmaSPRRAMWrite(i, self.cpu.dmaRAMRead(address))
            address += 1
            i+=1

    def readStatusFlag(self):
        value = 0
        value |= (self.vRamWrites << 4)
        value |= (self.scanlineSpriteCount << 5)
        value |= (self.sprite0Hit << 6)
        value |= (int(self.VBlank) << 7)

        self.firstWrite = True
        self.VBlank = False

        return value

    def doScanline(self):

        if self.showBackground:
            self.drawBackground()

        if self.showSprites:
            self.drawSprites()

    def drawBackground(self):
        matrix = pygame.PixelArray(self.layerB)
        tileY = int(self.cpu.scanline / 8)
        Y = int(self.cpu.scanline % 8)

        maxTiles = 32
        if (self.ppuScrollX % 8) != 0:
            maxTiles = 33

        currentTile = int(self.ppuScrollX / 8)
        v = int(self.nameTableAddress + currentTile)
        pixel = 0

        i=0 if self.clippingBackground else 1
        while i < maxTiles:

            fromByte = 0
            toByte = 8

            ppuScrollFlag = (self.ppuScrollX %8)
            if ppuScrollFlag != 0:
                if i == 0:
                    toByte = 7 - (ppuScrollFlag)
                if i == (maxTiles - 1):
                    fromByte = 8 - (ppuScrollFlag)

            ptrAddress = self.dmaVRAMRead(v + int(tileY*0x20))
            pattern1 = self.dmaVRAMRead(self.backgroundPatternTable + (ptrAddress*16) + Y)
            pattern2 = self.dmaVRAMRead(self.backgroundPatternTable + (ptrAddress*16) + Y + 8)
            # blockX and blockY block coodinate
            blockX = i % 4
            blockY = tileY % 4
            block = int(i / 4) + (int(tileY / 4) * 8)
            addressByte = int((v & ~0x001F) + 0x03C0 + block)
            byteAttributeTable = self.dmaVRAMRead(addressByte)
            colorIndex = 0x3F00

            if blockX < 2:
                if blockY >= 2:
                    colorIndex |= ((byteAttributeTable & 0b110000) >> 4) << 2
                else:
                    colorIndex |= (byteAttributeTable & 0b11) << 2
            elif blockX >= 2 and blockY < 2:
                colorIndex |= ((byteAttributeTable & 0b1100) >> 2) << 2
            else:
                colorIndex |= ((byteAttributeTable & 0b11000000) >> 6) << 2

            for j in range(fromByte, toByte):
                bit1 = ((1 << j) & pattern1) >> j
                bit2 = ((1 << j) & pattern2) >> j
                colorIndexFinal = colorIndex
                colorIndexFinal |= ((bit2 << 1) | bit1)

                color = self.colorPallete[self.dmaVRAMRead(colorIndexFinal)]
                x = (pixel + ((j * (-1)) + (toByte - fromByte) - 1))
                y = self.cpu.scanline

                if (color != matrix[x][y]):
                    matrix[x][y] = color

            pixel += toByte - fromByte

            if (v & 0x001f) == 31:
                v &= ~0x001F
                v ^= 0x400
            else:
                v += 1
            i+=1
        del matrix

    def drawSprites(self):
        numberSpritesPerScanline = 0
        Y = self.cpu.scanline % 8
        secondaryOAM = [0xFF] * 32
        indexSecondaryOAM = 0

        for currentSprite in range(0, 256, 4):
            spriteY = self.dmaSPRRAMRead(currentSprite)

            if numberSpritesPerScanline == 8:
                break

            if spriteY <= self.cpu.scanline < spriteY + self.spriteSize:
                for i in range(4):
                    secondaryOAM[indexSecondaryOAM + i] = self.dmaSPRRAMRead(currentSprite+i)
                indexSecondaryOAM += 4
                numberSpritesPerScanline += 1

        for currentSprite in range(28, -1, -4):
            spriteX = secondaryOAM[currentSprite + 3]
            spriteY = secondaryOAM[currentSprite]

            if spriteY >= 0xEF or spriteX >= 0xF9:
                continue

            currentSpriteAddress = currentSprite + 2
            flipVertical = secondaryOAM[currentSpriteAddress] & 0x80
            flipHorizontal = secondaryOAM[currentSpriteAddress] & 0x40

            Y = self.cpu.scanline - spriteY

            ptrAddress = secondaryOAM[currentSprite + 1]
            patAddress = self.spritePatternTable + (ptrAddress * 16) + ((7 - Y) if flipVertical else Y)
            pattern1 = self.dmaVRAMRead(patAddress)
            pattern2 = self.dmaVRAMRead(patAddress + 8)
            colorIndex = 0x3F10

            colorIndex |= ((secondaryOAM[currentSprite +2] & 0x3) << 2)

            for j in range(8):
                if flipHorizontal:
                    colorIndexFinal = (pattern1 >> j) & 0x1
                    colorIndexFinal |= ((pattern2 >> j) & 0x1 ) << 1
                else:
                    colorIndexFinal = (pattern1 >> (7 - j)) & 0x1
                    colorIndexFinal |= ((pattern2 >> (7 - j)) & 0x1) << 1

                colorIndexFinal += colorIndex
                if (colorIndexFinal % 4) == 0:
                    colorIndexFinal = 0x3F00
                color = self.colorPallete[(self.dmaVRAMRead(colorIndexFinal) & 0x3F)]

                # Add Transparency
                if color == self.colorPallete[self.dmaVRAMRead(0x3F10)]:
                    color += (0,)

                pygame.Surface.set_at(self.layerA, (spriteX + j, spriteY + Y), color)

                if self.showBackground and not(self.spriteHitOccured) and currentSprite == 0 and pygame.Surface.get_at(self.layerA, (spriteX + j, spriteY + Y)) == color:
                    self.sprite0Hit = True
                    self.spriteHitOccured = True

    def enterVBlank(self):
        if self.NMI:
            self.cpu.doNMI()

        self.VBlank = True
        self.screen.blit(self.layerB, (0,0))
        self.screen.blit(self.layerA, (0,0))
        self.screen.blit(self.debugLayer, (0,0))
        pygame.display.flip()

    def exitVBlank(self):
        self.VBlank = False
        self.debugLayer.fill((0,0,0,0))
        self.layerA.fill((0,0,0,0))
        self.layerB.fill((0,0,0))
        pygame.display.flip()

    def debugMsg(self, msg):
        self.debugLayer.fill((0,0,0,0))
        font = pygame.font.Font(pygame.font.get_default_font(), 8)
        self.debugLayer.blit(font.render(msg, False, (255, 255, 255, 1), (0,0,0,0)),(220,220))

#==================================================================================
# ADDRESSING MODE
#==================================================================================

def Zero(cpu):
    address = cpu.dmaRAMRead(cpu.registers['PC']+1)

    return address

def Zero_X(cpu):
    address = cpu.dmaRAMRead(cpu.registers['PC']+1)
    address = (address + cpu.registers['X']) & 0xFF

    return address

def Zero_Y(cpu):
    address = cpu.dmaRAMRead(cpu.registers['PC']+1)
    address = (address + cpu.registers['Y']) & 0xFF

    return address

def Absolute(cpu):
    addr1 = cpu.dmaRAMRead(cpu.registers['PC']+1)
    addr2 = cpu.dmaRAMRead(cpu.registers['PC']+2)
    address = ((addr2 << 8) | addr1) & 0xFFFF

    return address

def Absolute_X(cpu):
    addr1 = cpu.dmaRAMRead(cpu.registers['PC']+1)
    addr2 = cpu.dmaRAMRead(cpu.registers['PC']+2)
    address = (((addr2 << 8) | addr1) + cpu.registers['X']) & 0xFFFF

    return address

def Absolute_Y(cpu):
    addr1 = cpu.dmaRAMRead(cpu.registers['PC']+1)
    addr2 = cpu.dmaRAMRead(cpu.registers['PC']+2)
    address = (((addr2 << 8) | addr1) + cpu.registers['Y']) & 0xFFFF

    return address

def Indirect(cpu):
    addr1 = cpu.dmaRAMRead(cpu.registers['PC']+1)
    addr2 = cpu.dmaRAMRead(cpu.registers['PC']+2)
    addressTmp = addr2 << 8
    addressTmp += addr1

    address = cpu.dmaRAMRead(addressTmp) | (cpu.dmaRAMRead((addressTmp & 0xFF00) | ((addressTmp + 1) & 0x00FF)) << 8)

    return address

def Indirect_X(cpu):
    value = (cpu.dmaRAMRead(cpu.registers['PC']+1))
    addr1 = (cpu.dmaRAMRead((value + cpu.registers['X']) & 0xFF))
    addr2 = (cpu.dmaRAMRead((value + cpu.registers['X']+1) & 0xFF))
    address = ((addr2 << 8) | addr1) & 0xFFFF

    return address

def Indirect_Y(cpu):
    value = (cpu.dmaRAMRead(cpu.registers['PC']+1))
    addr1 = (cpu.dmaRAMRead(value))
    addr2 = (cpu.dmaRAMRead((value+1) & 0xFF))
    address = (((addr2 << 8) | addr1) + cpu.registers['Y']) & 0xFFFF

    return address

#==================================================================================
# EXEC INSTRUCTION
#==================================================================================

def rel_addr(value):
    if value & 0b10000000:
        value &= 0b1111111
        value -= 128

    return value

def advancePC(cpu, size):
    cpu.registers['PC'] += size

def setN(cpu, value):
    if value & (1<<7) == 1 << 7:
        cpu.setStatus(cpu.statusFlags['n'], 1)
    else:
        cpu.setStatus(cpu.statusFlags['n'], 0)

def setZ(cpu, value):
    if value == 0:
        cpu.setStatus(cpu.statusFlags['z'], 1)
    else:
        cpu.setStatus(cpu.statusFlags['z'], 0)

def setO(cpu, value):
    cpu.setStatus(cpu.statusFlags['v'], value)

def setC(cpu, value):
    cpu.setStatus(cpu.statusFlags['c'], value)

def ADC_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 255)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 255)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 255)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 255)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 255)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def ADC_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 255)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def AND_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.registers['A'] & cpu.readMemory(cpu.registers['PC']+1)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def AND_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def AND_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def AND_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def AND_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def AND_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def AND_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def AND_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    return nCycles

def ASL_Accumulator(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['A']
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['A'] = value
    return nCycles

def ASL_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ASL_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ASL_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ASL_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def BCC_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['c']) == False:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BCS_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['c']) == True:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BEQ_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['z']) == True:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BIT_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value & cpu.registers['A'])
    setO(cpu, (value >> 6) & 1)
    return nCycles

def BIT_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value & cpu.registers['A'])
    setO(cpu, (value >> 6) & 1)
    return nCycles

def BMI_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['n']) == True:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BNE_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['z']) == False:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BPL_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['n']) == False:
        nCycles += 1
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 1
        #cpu.registers['PC'] += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BRK_Implied(cpu):
    size = 1
    nCycles = 7

    cpu.registers['PC'] += 2
    cpu.pushStack((cpu.registers['PC'] >> 8) & 0xFF)
    cpu.pushStack(cpu.registers['PC'] & 0xFF)
    cpu.setStatus(cpu.statusFlags['b'], 1)
    cpu.pushStack(cpu.registers['P'])
    cpu.setStatus(cpu.statusFlags['i'], 1)
    cpu.registers['PC'] = (cpu.readMemory(0xFFFE) | (cpu.readMemory(0xFFFF) << 8))
    advancePC(cpu, size)
    return nCycles

def BVC_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['v']) == False:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def BVS_Relative(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = rel_addr(value)
    if cpu.getStatus(cpu.statusFlags['v']) == True:
        if (cpu.registers['PC'] & 0xFF00) != ((cpu.registers['PC'] + value) & 0xFF00):
            nCycles += 2
        else:
            nCycles += 1
        advancePC(cpu, value)
    advancePC(cpu, size)
    return nCycles

def CLC_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['c'], 0)
    advancePC(cpu, size)
    return nCycles

def CLD_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['d'], 0)
    advancePC(cpu, size)
    return nCycles

def CLI_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['i'], 0)
    advancePC(cpu, size)
    return nCycles

def CLV_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['v'], 0)
    advancePC(cpu, size)
    return nCycles

def CMP_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CMP_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CPX_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = cpu.registers['X'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CPX_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['X'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CPX_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['X'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CPY_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value = cpu.registers['Y'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CPY_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['Y'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def CPY_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = cpu.registers['Y'] - value
    advancePC(cpu, size)
    setC(cpu, 1 if value >= 0 else 0)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)
    return nCycles

def DEC_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def DEC_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def DEC_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def DEC_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def DEX_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['X']
    value = (value - 1) & 0xFF
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def DEY_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['Y']
    value = (value - 1) & 0xFF
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def EOR_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    value ^= cpu.registers['A']
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def INC_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def INC_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def INC_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def INC_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def INX_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['X']
    value = (value + 1) & 0xFF
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def INY_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['Y']
    value = (value + 1) & 0xFF
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def JMP_Absolute(cpu):
    size = 3
    nCycles = 3

    address = Absolute(cpu)
    advancePC(cpu, size)
    cpu.registers['PC'] = address
    return nCycles

def JMP_Indirect(cpu):
    size = 3
    nCycles = 5

    address = Indirect(cpu)
    advancePC(cpu, size)
    cpu.registers['PC'] = address
    return nCycles

def JSR_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    advancePC(cpu, 2)
    cpu.pushStack((cpu.registers['PC'] >> 8) & 0xFF)
    cpu.pushStack(cpu.registers['PC'] & 0xFF)
    cpu.registers['PC'] = address
    return nCycles

def LDA_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDA_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDX_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDX_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDX_Zero_Y(cpu):
    size = 2
    nCycles = 4

    address = Zero_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDX_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDX_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDY_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDY_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDY_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDY_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LDY_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LSR_Accumulator(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['A']
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LSR_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LSR_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LSR_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def LSR_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def NOP_Implied(cpu):
    size = 1
    nCycles = 2

    advancePC(cpu, size)
    return nCycles

def ORA_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def ORA_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    value |= cpu.registers['A']
    advancePC(cpu, size)
    cpu.registers['A'] = value
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def PHA_Implied(cpu):
    size = 1
    nCycles = 3

    value = cpu.registers['A']
    cpu.pushStack(value)
    advancePC(cpu, size)
    return nCycles

def PHP_Implied(cpu):
    size = 1
    nCycles = 3

    value = cpu.registers['P']
    cpu.pushStack(value)
    advancePC(cpu, size)
    return nCycles

def PLA_Implied(cpu):
    size = 1
    nCycles = 4

    value = cpu.pullStack()
    cpu.registers['A'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    return nCycles

def PLP_Implied(cpu):
    size = 1
    nCycles = 4

    value = cpu.pullStack()
    cpu.registers['P'] = (value & 0xEF)
    cpu.registers['P'] |= (1 << 5)
    advancePC(cpu, size)
    return nCycles

def ROL_Accumulator(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['A']
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['A'] = value
    return nCycles

def ROL_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROL_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROL_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROL_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROR_Accumulator(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['A']
    if cpu.getStatus(cpu.statusFlags['c']):
        value |= 0x100
    setC(cpu, value & 0x01)
    value >>= 1
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['A'] = value
    return nCycles

def ROR_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) + carry
    advancePC(cpu, size)
    setN(cpu, (value >> 7) & 1)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROR_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) + carry
    advancePC(cpu, size)
    setN(cpu, (value >> 7) & 1)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROR_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) + carry
    advancePC(cpu, size)
    setN(cpu, (value >> 7) & 1)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def ROR_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) + carry
    advancePC(cpu, size)
    setN(cpu, (value >> 7) & 1)
    setZ(cpu, value)
    cpu.writeMemory(address, value)
    return nCycles

def RTI_Implied(cpu):
    size = 1
    nCycles = 6

    value = cpu.pullStack()
    cpu.registers['P'] = value
    cpu.registers['P'] |= (1 << 5)
    value = cpu.pullStack()
    value |= (cpu.pullStack() << 8)
    cpu.registers['PC'] = value
    return nCycles

def RTS_Implied(cpu):
    size = 1
    nCycles = 6

    value = cpu.pullStack()
    value += ((cpu.pullStack()) << 8)
    cpu.registers['PC'] = value
    advancePC(cpu, size)
    return nCycles

def SBC_Immediate(cpu):
    size = 2
    nCycles = 2

    value = cpu.readMemory(cpu.registers['PC']+1)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Absolute_X(cpu):
    size = 3
    nCycles = 4

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SBC_Indirect_Y(cpu):
    size = 2
    nCycles = 5

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)
    return nCycles

def SEC_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['c'], 1)
    advancePC(cpu, size)
    return nCycles

def SED_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['d'], 1)
    advancePC(cpu, size)
    return nCycles

def SEI_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.setStatus(cpu.statusFlags['i'], 1)
    advancePC(cpu, size)
    return nCycles

def STA_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STA_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STA_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STA_Absolute_X(cpu):
    size = 3
    nCycles = 5

    address = Absolute_X(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STA_Absolute_Y(cpu):
    size = 3
    nCycles = 5

    address = Absolute_Y(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STA_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STA_Indirect_Y(cpu):
    size = 2
    nCycles = 6

    address = Indirect_Y(cpu)
    cpu.writeMemory(address, cpu.registers['A'])
    advancePC(cpu, size)
    return nCycles

def STX_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    cpu.writeMemory(address, cpu.registers['X'])
    advancePC(cpu, size)
    return nCycles

def STX_Zero_Y(cpu):
    size = 2
    nCycles = 4

    address = Zero_Y(cpu)
    cpu.writeMemory(address, cpu.registers['X'])
    advancePC(cpu, size)
    return nCycles

def STX_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    cpu.writeMemory(address, cpu.registers['X'])
    advancePC(cpu, size)
    return nCycles

def STY_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    cpu.writeMemory(address, cpu.registers['Y'])
    advancePC(cpu, size)
    return nCycles

def STY_Zero_X(cpu):
    size = 2
    nCycles = 4

    address = Zero_X(cpu)
    cpu.writeMemory(address, cpu.registers['Y'])
    advancePC(cpu, size)
    return nCycles

def STY_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    cpu.writeMemory(address, cpu.registers['Y'])
    advancePC(cpu, size)
    return nCycles

def TAX_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['A']
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    return nCycles

def TAY_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['A']
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['Y'] = value
    advancePC(cpu, size)
    return nCycles

def TSX_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['SP']
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['X'] = value
    advancePC(cpu, size)
    return nCycles

def TXA_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['X']
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    return nCycles

def TXS_Implied(cpu):
    size = 1
    nCycles = 2

    cpu.registers['SP'] = cpu.registers['X']
    advancePC(cpu, size)
    return nCycles

def TYA_Implied(cpu):
    size = 1
    nCycles = 2

    value = cpu.registers['Y']
    setN(cpu, value)
    setZ(cpu, value)
    cpu.registers['A'] = value
    advancePC(cpu, size)
    return nCycles

# Unofficial Opcodes
def DCP_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DCP_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DCP_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DCP_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DCP_Absolute_Y(cpu):
    size = 3
    nCycles = 7

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DCP_Indirect_X(cpu):
    size = 2
    nCycles = 8

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DCP_Indirect_Y(cpu):
    size = 2
    nCycles = 8

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    value = (value - 1) & 0xFF
    cpu.writeMemory(address, value)
    value = cpu.registers['A'] - value
    advancePC(cpu, size)
    setC(cpu, ~value >> 8 & 0x1)
    setN(cpu, value)
    setZ(cpu, value & 0xFF)

    return nCycles

def DOP_Immediate(cpu):
    size = 2
    nCycles = 2

    advancePC(cpu, size)
    return nCycles

def DOP_Zero(cpu):
    size = 2
    nCycles = 3

    advancePC(cpu, size)
    return nCycles

def DOP_Zero_X(cpu):
    size = 2
    nCycles = 4

    advancePC(cpu, size)
    return nCycles

def ISB_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def ISB_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def ISB_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def ISB_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def ISB_Absolute_Y(cpu):
    size = 3
    nCycles = 7

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def ISB_Indirect_X(cpu):
    size = 2
    nCycles = 8

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def ISB_Indirect_Y(cpu):
    size = 2
    nCycles = 8

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    value = (value + 1) & 0xFF
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = cpu.registers['A'] - value - (1 - carry)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    setO(cpu, (((cpu.registers['A'] ^ tmp) & 0x80) != 0 and ((cpu.registers['A'] ^ value) & 0x80) != 0))
    setC(cpu, 0 if tmp < 0 else 1)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def LAX_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)

    return nCycles

def LAX_Zero_Y(cpu):
    size = 2
    nCycles = 4

    address = Zero_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)

    return nCycles

def LAX_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)

    return nCycles

def LAX_Absolute_Y(cpu):
    size = 3
    nCycles = 4

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)

    return nCycles

def LAX_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)

    return nCycles

def LAX_Indirect_Y(cpu):
    size = 2
    nCycles = 6

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    cpu.registers['A'] = value
    cpu.registers['X'] = value
    advancePC(cpu, size)
    setN(cpu, value)
    setZ(cpu, value)

    return nCycles

def RLA_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RLA_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RLA_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RLA_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RLA_Absolute_Y(cpu):
    size = 3
    nCycles = 7

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RLA_Indirect_X(cpu):
    size = 2
    nCycles = 8

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RLA_Indirect_Y(cpu):
    size = 2
    nCycles = 8

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    setC(cpu, (value >> 7) & 1)
    value = ((value << 1) & 0xFF) + carry
    cpu.registers['A'] &= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])
    cpu.writeMemory(address, value)

    return nCycles

def RRA_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def RRA_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def RRA_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def RRA_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def RRA_Absolute_Y(cpu):
    size = 3
    nCycles = 7

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def RRA_Indirect_X(cpu):
    size = 2
    nCycles = 8

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def RRA_Indirect_Y(cpu):
    size = 2
    nCycles = 8

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    carry = (cpu.getStatus(cpu.statusFlags['c']) << 7)
    setC(cpu, value & 0x01)
    value = (value >> 1) | carry
    cpu.writeMemory(address, value)
    carry = cpu.getStatus(cpu.statusFlags['c'])
    tmp = value + cpu.registers['A'] + carry
    setO(cpu, not(((cpu.registers['A'] ^ value) & 0x80)!=0) and (((cpu.registers['A'] ^ tmp) & 0x80)))
    setC(cpu, tmp > 0xFF)
    setN(cpu, tmp)
    setZ(cpu, tmp & 0xFF)
    cpu.registers['A'] = (tmp & 0xFF)
    advancePC(cpu, size)

    return nCycles

def SAX_Zero(cpu):
    size = 2
    nCycles = 3

    address = Zero(cpu)
    value = cpu.registers['X'] & cpu.registers['A']
    cpu.writeMemory(address, value)
    advancePC(cpu, size)

    return nCycles

def SAX_Zero_Y(cpu):
    size = 2
    nCycles = 4

    address = Zero_Y(cpu)
    value = cpu.registers['X'] & cpu.registers['A']
    cpu.writeMemory(address, value)
    advancePC(cpu, size)

    return nCycles

def SAX_Absolute(cpu):
    size = 3
    nCycles = 4

    address = Absolute(cpu)
    value = cpu.registers['X'] & cpu.registers['A']
    cpu.writeMemory(address, value)
    advancePC(cpu, size)

    return nCycles

def SAX_Indirect_X(cpu):
    size = 2
    nCycles = 6

    address = Indirect_X(cpu)
    value = cpu.registers['X'] & cpu.registers['A']
    cpu.writeMemory(address, value)
    advancePC(cpu, size)

    return nCycles

def SLO_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SLO_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SLO_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SLO_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SLO_Absolute_Y(cpu):
    size = 3
    nCycles = 7

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SLO_Indirect_X(cpu):
    size = 2
    nCycles = 8

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SLO_Indirect_Y(cpu):
    size = 2
    nCycles = 8

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x80)
    value <<= 1
    value &= 0xFF
    cpu.writeMemory(address, value)
    cpu.registers['A'] |= value
    advancePC(cpu, size)
    setN(cpu, cpu.registers['A'])
    setZ(cpu, cpu.registers['A'])

    return nCycles

def SRE_Zero(cpu):
    size = 2
    nCycles = 5

    address = Zero(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def SRE_Zero_X(cpu):
    size = 2
    nCycles = 6

    address = Zero_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def SRE_Absolute(cpu):
    size = 3
    nCycles = 6

    address = Absolute(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def SRE_Absolute_X(cpu):
    size = 3
    nCycles = 7

    address = Absolute_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def SRE_Absolute_Y(cpu):
    size = 3
    nCycles = 7

    address = Absolute_Y(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def SRE_Indirect_X(cpu):
    size = 2
    nCycles = 8

    address = Indirect_X(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def SRE_Indirect_Y(cpu):
    size = 2
    nCycles = 8

    address = Indirect_Y(cpu)
    value = cpu.readMemory(address)
    setC(cpu, value & 0x01)
    value >>= 1
    cpu.registers['A'] ^= value
    cpu.writeMemory(address, value)
    advancePC(cpu, size)
    setZ(cpu, cpu.registers['A'])
    setN(cpu, cpu.registers['A'])

    return nCycles

def TOP_Absolute(cpu):
    size = 3
    nCycles = 4

    advancePC(cpu, size)
    return nCycles

def TOP_Absolute_X(cpu):
    size = 3
    nCycles = 4

    advancePC(cpu, size)
    return nCycles
#==================================================================================
# JOYSTICK
#==================================================================================

KeysBuffer__ = 0
ReadNumber__ = 0
LastWrote___ = 0

def Strobe():
    global KeysBuffer__, ReadNumber__, LastWrote___
    KeysBuffer__ = 0
    if ReadNumber__ == 0:
        if keys[pygame.K_a]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 1:
        if keys[pygame.K_s]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 2:
        if keys[pygame.K_SPACE]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 3:
        if keys[pygame.K_RETURN]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 4:
        if keys[pygame.K_UP]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 5:
        if keys[pygame.K_DOWN]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 6:
        if keys[pygame.K_LEFT]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 7:
        if keys[pygame.K_RIGHT]:
            KeysBuffer__ = 1
    elif ReadNumber__ == 16:
        KeysBuffer__ = 1
    ReadNumber__ += 1
    if ReadNumber__ > 23:
        ReadNumber__ = 0

#==================================================================================
# EXEC EMULATOR
#==================================================================================

class Exec:
    def __init__(self):
        romPath = sys.argv[1]
        self.cartridge = romLoader(romPath)
        self.cartridge.load()
        CPU = cpu(self.cartridge)
        CPU.run()

Exec()