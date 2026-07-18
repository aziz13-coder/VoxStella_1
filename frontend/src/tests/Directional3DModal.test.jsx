import React from 'react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Directional3DModal, {
  projectDirectionalCoordinate,
} from '../features/astroclock/Directional3DModal.jsx';

function buildPayload(overrides = {}) {
  return {
    systems: ['EQL', 'EQU', 'HOR'],
    body_policy: {
      scope: 'traditional',
      included: ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn'],
      excluded_points: ['North Node', 'South Node', 'Chiron'],
    },
    frame_context: {
      observer_frame: 'topocentric',
      azimuth_convention: 'north_zero_eastward',
      ecliptic_frame: 'geocentric_chart',
      equatorial_frame: 'geocentric_chart',
      horizon_frame: 'topocentric_observer',
      local_sidereal_time_deg: 87.25,
    },
    chart_info: {
      utc_datetime: '1990-01-13T19:33:00+00:00',
      latitude: 31.7683,
      longitude: 35.2137,
      rotation: 0,
      tilt: 0,
      house_system: 'R',
      house_system_requested: 'R',
      house_system_effective: 'R',
      house_system_source: 'chart',
      house_system_adjusted: false,
      polar_region: false,
      data_gaps: ['Moon latitude speed unavailable'],
    },
    objects: [
      {
        object_id: 'planet:Sun',
        object_type: 'planet',
        name: 'Sun',
        symbol: '\u2609',
        bfull: true,
        EQL: { longitude: 293.1, latitude: 0, speed: 1.02 },
        EQU: { longitude: 295.2, latitude: -21.4, speed: 0.98, latitude_speed: -0.1 },
        HOR: { longitude: 280.64, latitude: -12.4, speed: 90, latitude_speed: 12 },
        coordinate_meta: {
          EQL: { source: 'chart_ecliptic', speed_source: 'native' },
          EQU: { source: 'derived_from_ecliptic', speed_source: 'derived', latitude_speed_source: 'derived' },
          HOR: { source: 'swisseph_azalt', speed_source: 'finite_difference', latitude_speed_source: 'finite_difference' },
        },
      },
      {
        object_id: 'planet:Moon',
        object_type: 'planet',
        name: 'Moon',
        symbol: '\u263D',
        bfull: true,
        EQL: { longitude: 110, latitude: 4.2, speed: 13.1 },
        EQU: { longitude: 80, latitude: 25, speed: 12.8, latitude_speed: null },
        HOR: { longitude: 180, latitude: 0, speed: 0, latitude_speed: null },
        coordinate_meta: {
          EQL: { source: 'chart_ecliptic', speed_source: 'native' },
          EQU: {
            source: 'derived_from_ecliptic',
            speed_source: 'derived',
            latitude_speed_source: 'unavailable',
          },
          HOR: {
            source: 'topocentric_local_space',
            speed_source: 'unavailable',
            latitude_speed_source: 'unavailable',
          },
        },
      },
      {
        object_id: 'house:1',
        object_type: 'cusp',
        name: 'House 1',
        symbol: 'H1',
        bfull: false,
        EQL: { longitude: 124.72, latitude: 0, speed: 0 },
        EQU: { longitude: 126.1, latitude: 0, speed: 0 },
        HOR: { longitude: 90, latitude: 0, speed: 0 },
      },
      {
        object_id: '',
        name: '',
        HOR: { longitude: null, latitude: null },
      },
      {
        object_id: 'planet:Blank',
        name: 'Blank',
        EQL: { longitude: '   ', latitude: 0 },
        EQU: { longitude: true, latitude: 0 },
        HOR: { longitude: 0, latitude: 91 },
      },
    ],
    ...overrides,
  };
}

function defaultProps(overrides = {}) {
  return {
    open: true,
    onClose: vi.fn(),
    payload: buildPayload(),
    loading: false,
    error: '',
    ...overrides,
  };
}

describe('Directional3DModal projection', () => {
  it('keeps screen axes and camera depth independent', () => {
    const front = projectDirectionalCoordinate({ longitude: 0, latitude: 0 }, 0, 0);
    const east = projectDirectionalCoordinate({ longitude: 90, latitude: 0 }, 0, 0);
    const back = projectDirectionalCoordinate({ longitude: 180, latitude: 0 }, 0, 0);
    const northPole = projectDirectionalCoordinate({ longitude: 0, latitude: 90 }, 0, 0);

    expect(front).toMatchObject({ x: 160, y: 160, depth: 1, hidden: false });
    expect(east.x).toBeCloseTo(286, 6);
    expect(east.y).toBeCloseTo(160, 6);
    expect(east.depth).toBeCloseTo(0, 6);
    expect(back.depth).toBeCloseTo(-1, 6);
    expect(back.hidden).toBe(true);
    expect(northPole.y).toBeCloseTo(42, 6);
    expect(northPole.depth).toBeCloseTo(0, 6);
  });

  it('rejects incomplete coordinates instead of projecting them at zero', () => {
    expect(projectDirectionalCoordinate({ longitude: null, latitude: 0 }, 0, 0)).toBeNull();
    expect(projectDirectionalCoordinate({ longitude: 0, latitude: undefined }, 0, 0)).toBeNull();
    expect(projectDirectionalCoordinate({ longitude: '   ', latitude: 0 }, 0, 0)).toBeNull();
    expect(projectDirectionalCoordinate({ longitude: true, latitude: 0 }, 0, 0)).toBeNull();
    expect(projectDirectionalCoordinate({ longitude: 0, latitude: 91 }, 0, 0)).toBeNull();
  });

  it('uses a supplied backend unit vector when available', () => {
    const projected = projectDirectionalCoordinate(
      { longitude: 180, latitude: 0 },
      0,
      0,
      126,
      118,
      160,
      { x: 1, y: 0, z: 0 },
    );

    expect(projected).toMatchObject({ x: 160, y: 160, depth: 1, hidden: false });
  });
});

describe('Directional3DModal', () => {
  it('opens as an accessible Horizon view with directly selectable SVG objects', async () => {
    render(<Directional3DModal {...defaultProps()} />);

    const dialog = screen.getByRole('dialog', { name: 'Directional 3D' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: 'HOR', exact: true })).toHaveAttribute('aria-pressed', 'true');
    const chart = screen.getByRole('group', { name: 'Horizon Directional 3D chart' });
    expect(chart).toBeInTheDocument();
    expect(within(chart).getByRole('button', { name: 'Inspect Sun in Horizon coordinates' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(chart.querySelector('[data-directional-object="planet:Sun"]')).toBeTruthy();
    expect(chart.querySelector('[data-directional-object="planet:Moon"]')).toHaveAttribute(
      'data-directional-side',
      'back',
    );
    expect(screen.getByRole('button', { name: 'Back points' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('2 malformed object row(s) were rejected.')).toBeInTheDocument();
    expect(screen.getByText('Moon latitude speed unavailable')).toBeInTheDocument();
    expect(screen.getByLabelText('Directional model context')).toHaveTextContent('Bodies: Traditional (7)');
    expect(screen.getByLabelText('Directional model context')).toHaveTextContent('HOR: Topocentric Observer');
    expect(screen.getByLabelText('Directional model context')).toHaveTextContent('Azimuth: N 0° · E 90°');

    await waitFor(() => expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus());
  });

  it('changes selected objects from the visible sphere without starting an orbit drag', () => {
    render(<Directional3DModal {...defaultProps()} />);

    const chart = screen.getByRole('group', { name: 'Horizon Directional 3D chart' });
    const moonMarker = within(chart).getByRole('button', {
      name: 'Inspect Moon in Horizon coordinates',
    });
    const sunMarker = within(chart).getByRole('button', {
      name: 'Inspect Sun in Horizon coordinates',
    });
    const rotation = screen.getByRole('slider', { name: 'Directional rotation' });

    fireEvent.pointerDown(moonMarker, { button: 0, pointerId: 8, clientX: 120, clientY: 90 });
    fireEvent.pointerUp(moonMarker, { pointerId: 8, clientX: 120, clientY: 90 });
    fireEvent.click(moonMarker);

    expect(screen.getByLabelText('Directional object inspector')).toHaveTextContent(/Moon.*HOR/);
    expect(moonMarker).toHaveAttribute('aria-pressed', 'true');
    expect(rotation).toHaveValue('0');

    fireEvent.click(sunMarker);
    expect(screen.getByLabelText('Directional object inspector')).toHaveTextContent(/Sun.*HOR/);
    expect(sunMarker).toHaveAttribute('aria-pressed', 'true');

    fireEvent.keyDown(moonMarker, { key: ' ', code: 'Space' });
    expect(screen.getByLabelText('Directional object inspector')).toHaveTextContent(/Moon.*HOR/);
    expect(moonMarker).toHaveAttribute('aria-pressed', 'true');
  });

  it('selects the nearest displayed object when marker hit areas overlap', () => {
    render(<Directional3DModal {...defaultProps()} />);

    const chart = screen.getByRole('group', { name: 'Horizon Directional 3D chart' });
    const sunMarker = within(chart).getByRole('button', {
      name: 'Inspect Sun in Horizon coordinates',
    });
    const moonMarker = within(chart).getByRole('button', {
      name: 'Inspect Moon in Horizon coordinates',
    });
    const sunHitTarget = sunMarker.querySelector('[data-directional-hit-target="true"]');
    const sunX = Number(sunHitTarget?.getAttribute('cx'));
    const sunY = Number(sunHitTarget?.getAttribute('cy'));
    vi.spyOn(chart, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      top: 0,
      right: 320,
      bottom: 320,
      left: 0,
      width: 320,
      height: 320,
      toJSON: () => ({}),
    });

    // Simulate the browser targeting Moon's overlapping transparent circle while
    // the pointer itself is visually centred on the Sun glyph.
    fireEvent.click(moonMarker, { clientX: sunX, clientY: sunY });

    expect(screen.getByLabelText('Directional object inspector')).toHaveTextContent(/Sun.*HOR/);
    expect(sunMarker).toHaveAttribute('aria-pressed', 'true');
    expect(moonMarker).toHaveAttribute('aria-pressed', 'false');
  });

  it('uses three independent panes for All systems and labels their frames', () => {
    render(<Directional3DModal {...defaultProps()} />);

    fireEvent.click(screen.getByRole('button', { name: 'All systems' }));

    expect(screen.getByRole('button', { name: 'All systems' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/They are separated below so positions are not falsely co-registered/)).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Ecliptic Directional 3D chart' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Equatorial Directional 3D chart' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Horizon Directional 3D chart' })).toBeInTheDocument();
    expect(screen.getByText('Ecliptic (EQL)')).toBeInTheDocument();
    expect(screen.getByText('Equatorial (EQU)')).toBeInTheDocument();
    expect(screen.getByText('Horizon (HOR)')).toBeInTheDocument();
  });

  it('renders cusp points without inventing house-boundary surfaces', () => {
    render(<Directional3DModal {...defaultProps()} />);

    fireEvent.click(screen.getByRole('button', { name: 'EQL', exact: true }));
    const chart = screen.getByRole('group', { name: 'Ecliptic Directional 3D chart' });

    expect(screen.getByRole('button', { name: 'Cusp points' })).toHaveAttribute('aria-pressed', 'true');
    expect(chart.querySelector('[data-directional-house-cusp="house:1"]')).toBeTruthy();
    expect(chart.querySelector('[data-directional-house-boundary]')).toBeNull();
  });

  it('limits Back points honestly to markers while preserving reference orientation', () => {
    render(<Directional3DModal {...defaultProps()} />);
    const chart = screen.getByRole('group', { name: 'Horizon Directional 3D chart' });

    expect(chart.querySelector('[data-directional-object="planet:Moon"]')).toBeTruthy();
    expect(chart.querySelector('[data-directional-reference-plane="HOR"]')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Back points' }));

    expect(screen.getByRole('button', { name: 'Back points' })).toHaveAttribute('aria-pressed', 'false');
    expect(chart.querySelector('[data-directional-object="planet:Moon"]')).toBeNull();
    expect(chart.querySelector('[data-directional-reference-plane="HOR"]')).toBeTruthy();
  });

  it('does not let hidden back points displace visible labels', () => {
    const base = buildPayload();
    const payload = buildPayload({
      objects: [
        {
          ...base.objects[0],
          object_id: 'planet:Sun',
          name: 'Sun',
          HOR: { longitude: 0, latitude: 0, speed: 0, latitude_speed: 0 },
          vectors: undefined,
        },
        {
          ...base.objects[1],
          object_id: 'planet:Moon',
          name: 'Moon',
          HOR: { longitude: 180, latitude: 0, speed: 0, latitude_speed: 0 },
          vectors: undefined,
        },
      ],
    });
    render(<Directional3DModal {...defaultProps({ payload })} />);
    const chart = screen.getByRole('group', { name: 'Horizon Directional 3D chart' });
    const visibleLabel = () => chart.querySelector('[data-directional-object="planet:Sun"] text');

    expect(visibleLabel()).not.toHaveAttribute('x', '160');
    fireEvent.click(screen.getByRole('button', { name: 'Back points' }));

    expect(chart.querySelector('[data-directional-object="planet:Moon"]')).toBeNull();
    expect(visibleLabel()).toHaveAttribute('x', '160');
  });

  it('shows missing and unavailable values explicitly with correct coordinate labels', () => {
    render(<Directional3DModal {...defaultProps()} />);

    expect(screen.getByRole('columnheader', { name: /EQU RA/ })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /EQU Dec/ })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /HOR Az/ })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /HOR Alt/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Inspect Moon HOR Az/ }));
    const inspector = document.querySelector('[data-directional-inspector]');
    expect(within(inspector).getByText('Moon · HOR')).toBeInTheDocument();
    expect(within(inspector).getAllByText('Speed Unavailable').length).toBeGreaterThan(0);
    expect(within(inspector).getAllByText('Lat speed Unavailable').length).toBeGreaterThan(0);
    expect(within(inspector).getByText('Motion: Unavailable')).toBeInTheDocument();

    const objectHeader = screen.getByRole('columnheader', { name: /Object/ });
    expect(objectHeader).toHaveAttribute('aria-sort', 'ascending');
    fireEvent.click(within(objectHeader).getByRole('button', { name: /Object/ }));
    expect(objectHeader).toHaveAttribute('aria-sort', 'descending');
  });

  it('lets the table inspect an available scalar when the paired coordinate is missing', () => {
    const base = buildPayload();
    const payload = buildPayload({
      objects: base.objects.map((item) => (
        item.object_id === 'planet:Moon'
          ? { ...item, EQU: { ...item.EQU, latitude: null } }
          : item
      )),
    });
    render(<Directional3DModal {...defaultProps({ payload })} />);

    fireEvent.click(screen.getByRole('button', { name: 'EQU', exact: true }));
    fireEvent.click(screen.getByRole('button', { name: /Inspect Moon EQU RA/ }));

    expect(screen.getByLabelText('Directional object inspector')).toHaveTextContent(/Moon.*EQU/);
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
  });

  it('preserves camera and system-aware selection while stepped payloads load', () => {
    const props = defaultProps();
    const { rerender } = render(<Directional3DModal {...props} />);

    fireEvent.change(screen.getByRole('slider', { name: 'Directional rotation' }), {
      target: { value: '77' },
    });
    fireEvent.change(screen.getByRole('slider', { name: 'Directional tilt' }), {
      target: { value: '-24' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'All systems' }));
    fireEvent.click(screen.getByRole('button', { name: /Inspect Moon EQU RA/ }));

    const updatedPayload = buildPayload({
      objects: buildPayload().objects.map((item) => (
        item.object_id === 'planet:Moon'
          ? { ...item, EQU: { ...item.EQU, longitude: 81.5 } }
          : item
      )),
    });
    rerender(
      <Directional3DModal
        {...props}
        payload={updatedPayload}
        loading
      />,
    );

    expect(screen.getByRole('slider', { name: 'Directional rotation' })).toHaveValue('77');
    expect(screen.getByRole('slider', { name: 'Directional tilt' })).toHaveValue('-24');
    expect(screen.getByRole('button', { name: 'All systems' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Moon · EQU')).toBeInTheDocument();
    expect(screen.getByText('Loading Directional 3D…')).toHaveAttribute('role', 'status');

    fireEvent.click(screen.getByRole('button', { name: 'Reset view' }));
    expect(screen.getByRole('slider', { name: 'Directional rotation' })).toHaveValue('0');
    expect(screen.getByRole('slider', { name: 'Directional tilt' })).toHaveValue('0');
    expect(screen.getByRole('button', { name: 'HOR', exact: true })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Moon · HOR')).toBeInTheDocument();
  });

  it('initializes from the first async payload and preserves user camera through later payloads', () => {
    const props = defaultProps({ payload: null, loading: true });
    const { rerender } = render(<Directional3DModal {...props} />);
    const base = buildPayload();
    const initialPayload = buildPayload({
      chart_info: {
        ...base.chart_info,
        rotation: 9,
        tilt: 19,
      },
    });

    rerender(<Directional3DModal {...props} payload={initialPayload} loading={false} />);
    expect(screen.getByRole('slider', { name: 'Directional rotation' })).toHaveValue('9');
    expect(screen.getByRole('slider', { name: 'Directional tilt' })).toHaveValue('19');

    fireEvent.change(screen.getByRole('slider', { name: 'Directional rotation' }), {
      target: { value: '77' },
    });
    fireEvent.change(screen.getByRole('slider', { name: 'Directional tilt' }), {
      target: { value: '-24' },
    });
    const steppedPayload = buildPayload({
      chart_info: {
        ...base.chart_info,
        rotation: 33,
        tilt: 4,
      },
    });
    rerender(<Directional3DModal {...props} payload={steppedPayload} loading />);

    expect(screen.getByRole('slider', { name: 'Directional rotation' })).toHaveValue('77');
    expect(screen.getByRole('slider', { name: 'Directional tilt' })).toHaveValue('-24');

    fireEvent.click(screen.getByRole('button', { name: 'Reset view' }));
    expect(screen.getByRole('slider', { name: 'Directional rotation' })).toHaveValue('33');
    expect(screen.getByRole('slider', { name: 'Directional tilt' })).toHaveValue('4');
  });

  it('reconciles the selected frame on reopen and when a body lacks that coordinate', () => {
    const props = defaultProps();
    const { rerender } = render(<Directional3DModal {...props} />);

    fireEvent.click(screen.getByRole('button', { name: 'All systems' }));
    fireEvent.click(screen.getByRole('button', { name: /Inspect Moon EQU RA/ }));
    expect(screen.getByText('Moon · EQU')).toBeInTheDocument();

    rerender(<Directional3DModal {...props} open={false} />);
    rerender(<Directional3DModal {...props} open />);
    expect(screen.getByRole('button', { name: 'HOR', exact: true })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Moon · HOR')).toBeInTheDocument();

    const base = buildPayload();
    const payloadWithMissingHorizon = buildPayload({
      objects: base.objects.map((item) => (
        item.object_id === 'planet:Sun'
          ? { ...item, HOR: { longitude: null, latitude: null } }
          : item
      )),
    });
    rerender(<Directional3DModal {...props} payload={payloadWithMissingHorizon} open />);
    fireEvent.click(screen.getByRole('button', { name: 'EQL', exact: true }));
    fireEvent.click(screen.getByRole('button', { name: /Inspect Sun EQL Lon/ }));
    expect(screen.getByText('Sun · EQL')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'HOR', exact: true }));
    expect(screen.getByText('Moon · HOR')).toBeInTheDocument();
  });

  it('orbits by pointer drag while retaining keyboard sliders', () => {
    render(<Directional3DModal {...defaultProps()} />);
    const surface = document.querySelector('[data-directional-orbit-surface="HOR"]');
    const slider = screen.getByRole('slider', { name: 'Directional rotation' });

    fireEvent.pointerDown(surface, { button: 0, pointerId: 4, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(surface, { pointerId: 4, clientX: 110, clientY: 30 });
    fireEvent.pointerUp(surface, { pointerId: 4, clientX: 110, clientY: 30 });

    expect(slider).toHaveValue('60');
    expect(screen.getByRole('slider', { name: 'Directional tilt' })).toHaveValue('-9');
  });

  it('closes on Escape, restores focus, and restores body scrolling', async () => {
    const onClose = vi.fn();
    const trigger = document.createElement('button');
    trigger.textContent = 'Open Directional';
    document.body.appendChild(trigger);
    trigger.focus();
    const props = defaultProps({ onClose });
    const { rerender, unmount } = render(<Directional3DModal {...props} />);

    const closeButton = screen.getByRole('button', { name: 'Close' });
    await waitFor(() => expect(closeButton).toHaveFocus());
    expect(document.body.style.overflow).toBe('hidden');
    const dialog = screen.getByRole('dialog', { name: 'Directional 3D' });
    const enabledButtons = within(dialog).getAllByRole('button').filter((button) => !button.disabled);
    const lastButton = enabledButtons[enabledButtons.length - 1];
    lastButton.focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(closeButton).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(lastButton).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);

    rerender(<Directional3DModal {...props} open={false} />);
    await act(async () => {});
    expect(document.body.style.overflow).toBe('');
    expect(trigger).toHaveFocus();

    unmount();
    trigger.remove();
  });

  it('announces loading and errors while exposing dialog busy state', () => {
    const props = defaultProps({ payload: null, loading: true });
    const { rerender } = render(<Directional3DModal {...props} />);

    expect(screen.getByRole('dialog', { name: 'Directional 3D' })).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('Loading Directional 3D…')).toHaveAttribute('role', 'status');

    rerender(
      <Directional3DModal
        {...props}
        loading={false}
        error="Directional calculation failed"
      />,
    );
    expect(screen.getByRole('dialog', { name: 'Directional 3D' })).toHaveAttribute('aria-busy', 'false');
    expect(screen.getByRole('alert')).toHaveTextContent('Directional calculation failed');
  });
});
