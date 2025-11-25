const nextConfig = {
  output: 'standalone',  // 启用独立输出
  /* config options here */
  reactCompiler: true,
  optimizeFonts: false,
  experimental: {
    appDir: true
  },
   env: {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY, // 声明环境变量
  },
};

export default nextConfig;
