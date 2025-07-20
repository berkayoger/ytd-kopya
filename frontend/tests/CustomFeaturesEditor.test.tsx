import { render, screen, fireEvent } from '@testing-library/react';
import CustomFeaturesEditor from '../react/CustomFeaturesEditor';

describe('CustomFeaturesEditor', () => {
  it('renders without crashing', () => {
    render(<CustomFeaturesEditor />);
    expect(screen.getByText('Kullanıcıya Özel Özellikler')).toBeInTheDocument();
  });

  it('displays error on invalid JSON', async () => {
    render(<CustomFeaturesEditor />);
    const input = screen.getByLabelText(/custom_features JSON/i);
    fireEvent.change(input, { target: { value: '{invalid json' } });
    fireEvent.click(screen.getByText('Kaydet'));
    expect(await screen.findByText(/geçersiz json/i)).toBeInTheDocument();
  });
});
