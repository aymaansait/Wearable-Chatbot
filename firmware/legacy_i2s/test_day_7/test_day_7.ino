#include <driver/i2s.h>

constexpr gpio_num_t I2S_WS  = GPIO_NUM_15;
constexpr gpio_num_t I2S_SD  = GPIO_NUM_32;
constexpr gpio_num_t I2S_SCK = GPIO_NUM_14;

constexpr i2s_port_t I2S_PORT = I2S_NUM_0;
constexpr uint32_t SAMPLE_RATE = 16000;
constexpr uint32_t SERIAL_BAUD = 460800;
constexpr uint16_t FRAME_DURATION_MS = 20;
constexpr uint16_t FRAME_SIZE = SAMPLE_RATE * FRAME_DURATION_MS / 1000;

constexpr uint32_t FRAME_MAGIC = 0xAA55F00D;

static int32_t i2sReadBuffer[FRAME_SIZE];
static uint8_t txBuffer[sizeof(FRAME_MAGIC) + FRAME_SIZE * sizeof(int16_t)];

void setup()
{
    Serial.begin(SERIAL_BAUD);

    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD
    };

    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
    i2s_zero_dma_buffer(I2S_PORT);

    memcpy(txBuffer, &FRAME_MAGIC, sizeof(FRAME_MAGIC));
}

void loop()
{
    size_t bytesRead = 0;

    i2s_read(I2S_PORT, i2sReadBuffer, sizeof(i2sReadBuffer), &bytesRead, portMAX_DELAY);

    int samplesRead = bytesRead / sizeof(int32_t);
    int16_t* payload = reinterpret_cast<int16_t*>(txBuffer + sizeof(FRAME_MAGIC));

    for (int i = 0; i < samplesRead; i++)
    {
        int32_t sample24 = i2sReadBuffer[i] >> 8;
        int32_t sample16 = sample24 >> 9;

        if (sample16 > 32767)  sample16 = 32767;
        if (sample16 < -32768) sample16 = -32768;

        payload[i] = (int16_t)sample16;
    }

    Serial.write(txBuffer, sizeof(FRAME_MAGIC) + samplesRead * sizeof(int16_t));
}
