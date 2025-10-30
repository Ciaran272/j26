/**
 * DOM操作工具函数
 */

/**
 * 批量更新DOM（使用DocumentFragment提高性能）
 */
export function batchUpdateDOM(container, htmlArray) {
    const fragment = document.createDocumentFragment();
    
    htmlArray.forEach(html => {
        const p = document.createElement('p');
        p.innerHTML = html;
        fragment.appendChild(p);
    });
    
    // 一次性更新
    container.innerHTML = '';
    container.appendChild(fragment);
}

