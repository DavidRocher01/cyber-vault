import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { VaultService } from './vault.service';

describe('VaultService', () => {
  let service: VaultService;
  let httpMock: any;

  beforeEach(() => {
    httpMock = {
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    };
    service = new VaultService(httpMock);
  });

  it('getAll() appelle GET sur /vault/', () => {
    httpMock.get.mockReturnValue(of([]));
    service.getAll().subscribe();
    expect(httpMock.get).toHaveBeenCalledWith(expect.stringContaining('/vault/'));
  });

  it('create() appelle POST sur /vault/ avec le payload', () => {
    const payload = { title: 'GitHub', password_encrypted: 'enc123' };
    httpMock.post.mockReturnValue(of({ id: 1, ...payload, username: null, url: null, notes: null }));
    service.create(payload).subscribe();
    expect(httpMock.post).toHaveBeenCalledWith(expect.stringContaining('/vault/'), payload);
  });

  it('delete() appelle DELETE sur /vault/:id', () => {
    httpMock.delete.mockReturnValue(of(null));
    service.delete(42).subscribe();
    expect(httpMock.delete).toHaveBeenCalledWith(expect.stringContaining('/vault/42'));
  });

  it('update() appelle PATCH sur /vault/:id avec le payload', () => {
    const payload = { title: 'Nouveau titre' };
    httpMock.patch.mockReturnValue(of({ id: 1, ...payload }));
    service.update(1, payload).subscribe();
    expect(httpMock.patch).toHaveBeenCalledWith(expect.stringContaining('/vault/1'), payload);
  });
});
