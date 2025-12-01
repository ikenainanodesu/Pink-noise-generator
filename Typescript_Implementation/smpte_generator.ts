// smpte_generator.ts

// 定义配置接口
export interface GeneratorConfig {
  sampleRate: 48000 | 96000;
  duration: number;
  channels: number;
  onProgress?: (percent: number) => void;
}

export interface GenerationResult {
  blob: Blob;
  url: string;
  rmsDb: number;
  duration: number;
  filename: string;
  previewData: Float32Array; // 用于波形绘制
}

export class SmptePinkNoiseGenerator {
  private config: GeneratorConfig;

  // 常量定义
  private readonly SAMPLE_SIZE = 3; // 24-bit
  private readonly MAX_PEAK_DB = -9.5;

  constructor(config: GeneratorConfig) {
    this.config = config;
  }

  public async generate(): Promise<GenerationResult> {
    const { sampleRate, duration, channels, onProgress } = this.config;

    // 参数初始化
    let samplesPerPeriod = 524288;
    let randStep = 52737;

    if (sampleRate > 48000) {
      samplesPerPeriod = 1048576;
      randStep = 163841;
    }

    const randMax = samplesPerPeriod - 1;
    let seed = 0;
    let white = 0.0;
    const scaleFactor = 2.0 / randMax;

    // 滤波器参数计算
    const maxAmp = Math.pow(10.0, this.MAX_PEAK_DB / 20.0);
    const hpFc = 10.0;
    let lpFc = 22400.0;
    if (lpFc > sampleRate / 2.0) lpFc = sampleRate / 2.0;

    const w0t = (2.0 * Math.PI * hpFc) / sampleRate;
    const k = Math.tan((2.0 * Math.PI * lpFc) / sampleRate / 2.0);
    const k2 = k * k;

    // Biquad 系数计算 (HP1, HP2, LP1, LP2)
    // HP1
    const hp1_a1 =
      -2.0 * Math.exp(-0.3826835 * w0t) * Math.cos(0.9238795 * w0t);
    const hp1_a2 = Math.exp(2.0 * -0.3826835 * w0t);
    const hp1_b0 = (1.0 - hp1_a1 + hp1_a2) / 4.0;
    const hp1_b1 = -2.0 * hp1_b0;
    const hp1_b2 = hp1_b0;

    // HP2
    const hp2_a1 =
      -2.0 * Math.exp(-0.9238795 * w0t) * Math.cos(0.3826835 * w0t);
    const hp2_a2 = Math.exp(2.0 * -0.9238795 * w0t);
    const hp2_b0 = (1.0 - hp2_a1 + hp2_a2) / 4.0;
    const hp2_b1 = -2.0 * hp2_b0;
    const hp2_b2 = hp2_b0;

    // LP1
    const lp1_denom = k2 + k / 1.306563 + 1.0;
    const lp1_a1 = (2.0 * (k2 - 1.0)) / lp1_denom;
    const lp1_a2 = (k2 - k / 1.306563 + 1.0) / lp1_denom;
    const lp1_b0 = k2 / lp1_denom;
    const lp1_b1 = 2.0 * lp1_b0;
    const lp1_b2 = lp1_b0;

    // LP2
    const lp2_denom = k2 + k / 0.541196 + 1.0;
    const lp2_a1 = (2.0 * (k2 - 1.0)) / lp2_denom;
    const lp2_a2 = (k2 - k / 0.541196 + 1.0) / lp2_denom;
    const lp2_b0 = k2 / lp2_denom;
    const lp2_b1 = 2.0 * lp2_b0;
    const lp2_b2 = lp2_b0;

    // 状态变量初始化
    let hp1w1 = 0.0,
      hp1w2 = 0.0,
      hp2w1 = 0.0,
      hp2w2 = 0.0;
    let lp1w1 = 0.0,
      lp1w2 = 0.0,
      lp2w1 = 0.0,
      lp2w2 = 0.0;
    let pink = 0.0;
    let p_lp1 = 0.0,
      p_lp2 = 0.0,
      p_lp3 = 0.0,
      p_lp4 = 0.0,
      p_lp5 = 0.0,
      p_lp6 = 0.0;

    // 样本总数计算
    let totalSamples = samplesPerPeriod + sampleRate * duration;
    const diff = totalSamples % samplesPerPeriod;
    if (diff !== 0) totalSamples += samplesPerPeriod - diff;

    // 准备 WAV 数据缓冲区
    const outputSamples = totalSamples - samplesPerPeriod;
    const dataLength = this.SAMPLE_SIZE * outputSamples * channels;
    const headerLength = 44;
    const buffer = new ArrayBuffer(headerLength + dataLength);
    const view = new DataView(buffer);

    // 写入 WAV 头部
    this.writeWavHeader(view, dataLength, sampleRate, channels);

    // 生成音频数据
    let accum = 0.0;
    let writeOffset = 44;

    // 用于预览的数据 (降采样)
    const previewSize = 1000;
    const previewStep = Math.floor(outputSamples / previewSize);
    const previewData = new Float32Array(previewSize);
    let previewIndex = 0;

    // 批处理大小，避免阻塞 UI
    const batchSize = 10000;

    for (let i = 0; i < totalSamples; i++) {
      // 异步让渡主线程，保持 UI 响应
      if (i % batchSize === 0) {
        if (onProgress) onProgress(i / totalSamples);
        await new Promise((resolve) => setTimeout(resolve, 0));
      }

      // LCG PRNG
      seed = (1664525 * seed + randStep) & randMax;
      white = seed * scaleFactor - 1.0;

      // Pink Filter Network
      p_lp1 = 0.9994551 * p_lp1 + 0.00198166688621989 * white;
      p_lp2 = 0.9969859 * p_lp2 + 0.00263702334184061 * white;
      p_lp3 = 0.984447 * p_lp3 + 0.00643213710202331 * white;
      p_lp4 = 0.9161757 * p_lp4 + 0.0143895253836282 * white;
      p_lp5 = 0.6563399 * p_lp5 + 0.0269840854106461 * white;
      const pinkVal =
        p_lp1 +
        p_lp2 +
        p_lp3 +
        p_lp4 +
        p_lp5 +
        p_lp6 +
        white * 0.0342675832159306;
      p_lp6 = white * 0.0088766118009356;

      pink = pinkVal;

      // Bandpass Filters (Direct Form II)
      let w = pink - hp1_a1 * hp1w1 - hp1_a2 * hp1w2;
      pink = hp1_b0 * w + hp1_b1 * hp1w1 + hp1_b2 * hp1w2;
      hp1w2 = hp1w1;
      hp1w1 = w;

      w = pink - hp2_a1 * hp2w1 - hp2_a2 * hp2w2;
      pink = hp2_b0 * w + hp2_b1 * hp2w1 + hp2_b2 * hp2w2;
      hp2w2 = hp2w1;
      hp2w1 = w;

      w = pink - lp1_a1 * lp1w1 - lp1_a2 * lp1w2;
      pink = lp1_b0 * w + lp1_b1 * lp1w1 + lp1_b2 * lp1w2;
      lp1w2 = lp1w1;
      lp1w1 = w;

      w = pink - lp2_a1 * lp2w1 - lp2_a2 * lp2w2;
      pink = lp2_b0 * w + lp2_b1 * lp2w1 + lp2_b2 * lp2w2;
      lp2w2 = lp2w1;
      lp2w1 = w;

      // Limit Peaks
      if (pink > maxAmp) pink = maxAmp;
      else if (pink < -maxAmp) pink = -maxAmp;

      // 仅在预热期过后记录数据
      if (i > randMax) {
        accum += pink * pink;

        // 收集预览数据
        if ((i - randMax) % previewStep === 0 && previewIndex < previewSize) {
          previewData[previewIndex++] = pink;
        }

        // 24-bit PCM 转换
        // Python: int(pink * 2147483647.0) 然后取 [1:] (即丢弃最低字节，保留高3字节)
        // 这里我们模拟这个逻辑：计算 32位整数，然后写入高24位
        let sampleInt = Math.floor(pink * 2147483647.0);

        // 处理边界
        if (sampleInt > 2147483647) sampleInt = 2147483647;
        if (sampleInt < -2147483648) sampleInt = -2147483648;

        // 写入声道
        for (let ch = 0; ch < channels; ch++) {
          // 获取 32位 整数的字节
          // Little Endian: LSB 在低地址。Python 代码丢弃了 LSB (index 0)。
          // 所以我们需要写入 Byte 1, Byte 2, Byte 3。

          const byte1 = (sampleInt >> 8) & 0xff;
          const byte2 = (sampleInt >> 16) & 0xff;
          const byte3 = (sampleInt >> 24) & 0xff;

          view.setUint8(writeOffset, byte1);
          view.setUint8(writeOffset + 1, byte2);
          view.setUint8(writeOffset + 2, byte3);

          writeOffset += 3;
        }
      }
    }

    // 计算 RMS
    const rms = 10.0 * Math.log10(accum / outputSamples);

    const blob = new Blob([buffer], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);

    return {
      blob,
      url,
      rmsDb: rms + 3.01, // 加上 3.01 dB 得到 AES17 标准值
      duration,
      filename: "pink_noise_output.wav",
      previewData,
    };
  }

  private writeString(view: DataView, offset: number, string: string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  private writeWavHeader(
    view: DataView,
    dataLength: number,
    sampleRate: number,
    channels: number
  ) {
    // RIFF chunk descriptor
    this.writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + dataLength, true); // ChunkSize
    this.writeString(view, 8, "WAVE");

    // fmt sub-chunk
    this.writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
    view.setUint16(22, channels, true); // NumChannels
    view.setUint32(24, sampleRate, true); // SampleRate
    view.setUint32(28, sampleRate * channels * 3, true); // ByteRate (SampleRate * BlockAlign)
    view.setUint16(32, channels * 3, true); // BlockAlign (NumChannels * BitsPerSample/8)
    view.setUint16(34, 24, true); // BitsPerSample (24 bits)

    // data sub-chunk
    this.writeString(view, 36, "data");
    view.setUint32(40, dataLength, true); // Subchunk2Size
  }
}
