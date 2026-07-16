#include "driver/i2s_std.h"
#include <math.h>

// =====================================================
// GPIO Configuration
// =====================================================
constexpr gpio_num_t I2S_WS  = GPIO_NUM_7;
constexpr gpio_num_t I2S_SD  = GPIO_NUM_9;
constexpr gpio_num_t I2S_SCK = GPIO_NUM_5;

// =====================================================
// Audio Configuration
// =====================================================
constexpr uint32_t SAMPLE_RATE = 16000;
constexpr uint32_t SERIAL_BAUD = 460800;
constexpr uint16_t FRAME_DURATION_MS = 20;
constexpr uint16_t FRAME_SIZE =
    SAMPLE_RATE * FRAME_DURATION_MS / 1000;

constexpr uint32_t FRAME_MAGIC = 0xAA55F00D;

// Soft-limiter parameters.
// Below THRESHOLD, samples pass through unchanged (quiet speech
// stays exactly as loud as it naturally is). Above THRESHOLD,
// samples are compressed smoothly toward the ceiling using a
// tanh curve instead of being hard-clipped, which is what was
// causing the crackling distortion on close/loud speech.
constexpr float LIMITER_THRESHOLD = 24000.0f;
constexpr float LIMITER_CEILING   = 32000.0f;

static int32_t i2sReadBuffer[FRAME_SIZE];

static uint8_t txBuffer[
    sizeof(FRAME_MAGIC) +
    FRAME_SIZE * sizeof(int16_t)
];

i2s_chan_handle_t rx_handle;

int16_t softLimit(float x)
{
    float sign = (x < 0) ? -1.0f : 1.0f;
    float mag = fabsf(x);

    if (mag <= LIMITER_THRESHOLD)
    {
        return (int16_t)x;
    }

    float over = mag - LIMITER_THRESHOLD;
    float range = LIMITER_CEILING - LIMITER_THRESHOLD;
    float compressed = LIMITER_THRESHOLD + range * tanhf(over / range);

    return (int16_t)(sign * compressed);
}

void setup()
{
    Serial.begin(SERIAL_BAUD);
    delay(1000);

    Serial.println();
    Serial.println("ESP32-S3 Starting...");

    i2s_chan_config_t chan_cfg =
        I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    i2s_new_channel(&chan_cfg, NULL, &rx_handle);

    i2s_std_config_t std_cfg = {
        .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
                        I2S_DATA_BIT_WIDTH_32BIT,
                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = I2S_SCK,
            .ws   = I2S_WS,
            .dout = I2S_GPIO_UNUSED,
            .din  = I2S_SD,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv   = false,
            },
        },
    };

    std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;

    i2s_channel_init_std_mode(rx_handle, &std_cfg);
    i2s_channel_enable(rx_handle);

    memcpy(txBuffer, &FRAME_MAGIC, sizeof(FRAME_MAGIC));

    Serial.println("Audio Stream Ready");
}

void loop()
{
    size_t bytesRead = 0;

    i2s_channel_read(
        rx_handle,
        i2sReadBuffer,
        sizeof(i2sReadBuffer),
        &bytesRead,
        portMAX_DELAY
    );

    int samplesRead = bytesRead / sizeof(int32_t);

    int16_t* payload =
        reinterpret_cast<int16_t*>(txBuffer + sizeof(FRAME_MAGIC));

    for (int i = 0; i < samplesRead; i++)
    {
        int32_t sample24 = i2sReadBuffer[i] >> 8;
        float sample16f = (float)(sample24 >> 9);   // baseline gain, good for quiet/far speech

        payload[i] = softLimit(sample16f);
    }

    Serial.write(
        txBuffer,
        sizeof(FRAME_MAGIC) + samplesRead * sizeof(int16_t)
    );
}
