// Cấu hình commitlint — bắt buộc Conventional Commits (https://www.conventionalcommits.org).
// Dùng bởi .github/workflows/commitlint.yml. Đặt ở thư mục gốc repo.
// Dùng .mjs (ESM) để khớp loại module action yêu cầu, tránh lỗi "module is not defined".
export default {
  extends: ['@commitlint/config-conventional'],
};
