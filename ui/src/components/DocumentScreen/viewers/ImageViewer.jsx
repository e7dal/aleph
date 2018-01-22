import React, { PureComponent } from 'react';
import { connect } from 'react-redux';
import SectionLoading from 'src/components/common/SectionLoading';

import './ImageViewer.css';

class ImageViewer extends PureComponent {
  render() {
    const { document, session } = this.props;
    if (!document.links || !document.links.file) {
        return <SectionLoading />;
    }
    const imageUrl = session.token ? `${document.links.file}?api_key=${session.token}` : document.links.file;

    return (
      <div className="ImageViewer">
        <img src={imageUrl} alt={document.file_name} />
      </div>
    );
  }
}

const mapStateToProps = state => ({
  session: state.session,
});

export default connect(mapStateToProps)(ImageViewer);