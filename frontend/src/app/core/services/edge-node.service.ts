import { inject, Injectable } from '@angular/core';
import { edgeNodeApiEndpoints } from '@environments';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ICreateEdgeNodeRequest, ICreateEdgeNodeResponse, IEdgeNode } from '@shared/interfaces/edge-node';

@Injectable({
  providedIn: 'root',
})
export class EdgeNodeService {
   private readonly httpClient = inject(HttpClient);

  createEdgeNode(
    body: ICreateEdgeNodeRequest
  ): Observable<ICreateEdgeNodeResponse> {
    return this.httpClient.post<ICreateEdgeNodeResponse>(
      edgeNodeApiEndpoints.createEdgeNode,
      body
    );
  }

  getEdgeNodes(): Observable<IEdgeNode[]> {
    return this.httpClient.get<IEdgeNode[]>(
      edgeNodeApiEndpoints.getEdgeNodes
    );
  }

  getEdgeNodeById(id: string): Observable<IEdgeNode> {
    return this.httpClient.get<IEdgeNode>(
      edgeNodeApiEndpoints.getEdgeNodeById(id)
    );
  }

  updateEdgeNode(id: string, body: Partial<IEdgeNode>): Observable<IEdgeNode> {
    return this.httpClient.patch<IEdgeNode>(
      edgeNodeApiEndpoints.updateEdgeNode(id),
      body
    );
  }

  deleteEdgeNode(id: string): Observable<void> {
    return this.httpClient.delete<void>(
      edgeNodeApiEndpoints.deleteEdgeNode(id)
    );
  }
}
